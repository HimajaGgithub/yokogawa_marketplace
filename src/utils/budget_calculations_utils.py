import os
from enum import Enum
from typing import Literal
from uuid import UUID

import numpy as np
import pandas as pd

from src.assets.agent_db import Config
from src.properties.market_prices import market_prices, unit_quantity

table_fmt = "mixed_grid"


def print_aligned_table_with_bold_footer(data: pd.DataFrame, footer_data):
    try:
        from tabulate import tabulate
    except ImportError:
        print("WARNING: Tabulate not found.")
        return ""
    num_columns = len(data.columns)
    footer_cols = len(footer_data[0])
    padding = [""] * (num_columns - footer_cols)
    padded_footer_data = padding + footer_data[0]
    combined_data = [list(data.columns)]
    for x in data.to_records(index=False):
        row = []
        for y in x:
            if isinstance(y, np.ndarray):
                row.append(y.tolist())
            else:
                row.append(y)
        combined_data.append(row)
    combined_data.append(padded_footer_data)

    mixed_table = tabulate(combined_data, headers="firstrow", tablefmt="mixed_grid")
    heavy_table = tabulate(combined_data, headers="firstrow", tablefmt="heavy_grid")
    mixed_lines = mixed_table.splitlines()
    heavy_lines = heavy_table.splitlines()

    bold_footer_line = heavy_lines[-3]
    bold_footer_line = bold_footer_line.replace('╋', '╈').replace('┣', '┢').replace('┫', '┪')

    reconstructed_table_lines = mixed_lines[:-3] + [bold_footer_line] + heavy_lines[-2:]
    return "<pre>" + "\n".join(reconstructed_table_lines) + "</pre>"


def plot_quotes(product, materials, buyer_quotes, seller_quotes, buyer_accept, seller_accept):
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print("WARNING: Plotly not found.")
        return ""

    num_materials = len(materials)
    num_rounds = len(buyer_quotes[0])
    x_vals = [f"Round {i + 1}" for i in range(num_rounds)]
    ncols = 2
    nrows = int(np.ceil(num_materials / ncols))

    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=[m.title() + " Quotes" for m in materials],
        shared_xaxes=False
    )

    for idx, material in enumerate(materials):
        row, col = idx // ncols + 1, idx % ncols + 1

        # --- Buyer & Seller curves ---
        curves = [
            (buyer_quotes[idx], "Buyer", "blue", "dot"),
            (seller_quotes[idx], "Seller", "red", "solid")
        ]
        for y, name, color, dash in curves:
            fig.add_trace(go.Scatter(
                x=x_vals, y=y, mode="lines+markers", name=name,
                line=dict(color=color, dash=dash),
                legendgroup=name, showlegend=(idx == 0)
            ), row=row, col=col)

        # --- Agreement / Disagreement markers ---
        agreement = buyer_accept[idx] & seller_accept[idx]
        disagreement = ~agreement

        markers = [
            (agreement, "Agreement", "green", "star", 12),
            (disagreement, "No Agreement", "red", "x", 8)
        ]
        for mask, name, color, symbol, size in markers:
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=np.array(x_vals)[mask],
                    y=buyer_quotes[idx][mask],
                    mode="markers", name=name,
                    marker=dict(color=color, size=size, symbol=symbol),
                    legendgroup=name, showlegend=(idx == 0)
                ), row=row, col=col)

        # --- Y-axis range per subplot ---
        ymin = min(buyer_quotes[idx].min(), seller_quotes[idx].min())
        ymax = max(buyer_quotes[idx].max(), seller_quotes[idx].max())
        fig.update_yaxes(autorange=False, range=[ymin * 0.95, ymax * 1.05], row=row, col=col)

    fig.update_layout(
        height=400 * nrows, width=900,
        title=f"Negotiation Quotes for {product.upper()}",
        template="plotly_white"
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def exp_decay_quotes(start, end, num=6, p=2):
    """
    Seller quotes: high -> low. Decrease fast initially, then flatten.
    """
    x = np.linspace(0, 1, num)
    return start + (end - start) * (x ** p)


def exp_growth_quotes(start, end, num=6, p=2):
    """
    Buyer quotes: low -> high. Increase fast initially, then flatten.
    """
    x = np.linspace(0, 1, num)
    return start + (end - start) * (1 - (1 - x) ** p)


class NegotiationScheme(str, Enum):
    price = "price"
    margin = "margin"
    distribution = "distribution"


def interpolate(percentages, minimum, maximum):
    if isinstance(percentages, list):
        percentages = np.array(percentages)
    return minimum + ((percentages/100) * (maximum - minimum))


def get_quotes(listing, role=Literal["buyer", "seller"]):
    model = listing['payload'].get("negotiation_model", None)
    if not model:
        model = Config.get(Config.key == "negotiation_model").value

    print("Using negotiation model", model)
    if model[f'{role}_scheme'] == NegotiationScheme.price.value:
        prices = np.array(model[f'{role}_prices'])
    elif model[f'{role}_scheme'] == NegotiationScheme.margin.value:
        margins = np.array(model[f"{role}_margins"])
        prices = (margins/100) * market_prices[listing['material_code']]
    elif model[f'{role}_scheme'] == NegotiationScheme.distribution.value:
        budget_min = market_prices[listing['material_code']] * (model[f"{role}_margin_min"] / 100)
        budget_max = market_prices[listing['material_code']] * (model[f"{role}_margin_max"] / 100)
        print("budget min, max", budget_min, budget_max)
        prices = interpolate(model[f"{role}_distribution"], budget_min, budget_max)
        print("distribution", model[f"{role}_distribution"])
    else:
        raise NotImplementedError
    print("Base Prices for", listing['material_code'], prices)
    prices = prices * listing['quantity']
    result = sorted(prices.round(2).tolist(), reverse=(role == "seller"))
    print("Final Prices for", role, listing['quantity'], listing['quantity_unit'], result)
    return result


def get_costs(product):
    materials = [x[0] for x in unit_quantity[product].values()]
    quantities = [[x[1]] for x in unit_quantity[product].values()]
    q_strings = [f"{x[1]} {x[2]}" for x in unit_quantity[product].values()]
    product_strings = [product for _ in unit_quantity[product].values()]

    prices = [market_prices[x[0]] for x in unit_quantity[product].values()]
    material_costs = np.array(quantities) * prices

    b_quotes, b_acceptance_factor = [], []
    s_quotes, s_acceptance_factor = [], []

    for m, q in zip(materials, quantities):
        buyer_quote, acceptance_factor = get_quotes(m, q[0], role="buyer")
        b_quotes.append(buyer_quote)
        b_acceptance_factor.append(acceptance_factor)

        seller_quote, acceptance_factor = get_quotes(m, q[0], role="seller")
        s_quotes.append(seller_quote)
        s_acceptance_factor.append(acceptance_factor)

    buyer_quotes = np.array(b_quotes)
    seller_quotes = np.array(s_quotes)
    min_n = min(buyer_quotes.shape[1], seller_quotes.shape[1])

    buyer_quotes = buyer_quotes[:, :min_n]
    seller_quotes = seller_quotes[:, :min_n]

    buyer_acceptance_factor = np.array(b_acceptance_factor).reshape(-1, 1)
    seller_acceptance_factor = np.array(s_acceptance_factor).reshape(-1, 1)
    buyer_accept = seller_quotes < buyer_quotes * buyer_acceptance_factor
    seller_accept = buyer_quotes > seller_quotes * seller_acceptance_factor

    result = pd.DataFrame(
        list(zip(product_strings, materials, q_strings, prices, material_costs, buyer_quotes, seller_quotes,
                 buyer_acceptance_factor, seller_acceptance_factor, buyer_accept, seller_accept)),
        columns=['product', 'material', 'quantity', "unit_cost_price", 'cost', "buyer quotes", "seller quotes",
                 "buyer_acceptance_factor", "seller_acceptance_factor", "buyer_accept", "seller_accept"]
    )
    return result


def generate_html():
    if os.getenv("env", "") == "cloud":
        return ""
    try:
        from tabulate import tabulate
    except ImportError:
        print("WARNING: Tabulate not found.")
        return ""
    html = '<script src="https://cdn.plot.ly/plotly-3.1.0.min.js" charset="utf-8"></script>'
    html += "<h2>Budget calculations</h2>"
    data = {
        "selling_price": "selling_price = cost_price + profit",
        "details": "selling_price = (procurement_cost + logistics_costs + processing_costs) * (profit_margin))"
    }

    html += "<pre>"
    html += tabulate(zip(data.keys(), data.values()), tablefmt=table_fmt)
    html += "</pre>"

    data = []
    for k, v in market_prices.items():
        data.append([k, v.tolist(), np.round(v.mean(), 2)])

    html += "<pre>"
    html += tabulate(data, headers=["Material", "Market Price (min, max)", "Average Market Price"], tablefmt=table_fmt)
    html += "</pre>"

    for product in unit_quantity:
        html += "<h2>" + product + "</h2>"
        df = get_costs(product)

        total_materials_cost = np.round(np.sum(df['cost'], axis=0), 2).tolist()
        html += print_aligned_table_with_bold_footer(
            data=df,
            footer_data=[
                [f"Market price: {market_prices[product]}", "", "", "Total materials cost:",
                 total_materials_cost,
                 "", "", "", "", "", ""]],
        )
        html += plot_quotes(product, df['material'], df['buyer quotes'], df['seller quotes'], df['buyer_accept'],
                            df['seller_accept'])
    return html


def get_auction_bid(listing, n, bids_total=10):
    product = listing['material_code']
    quantity = listing['quantity']
    price = market_prices[product]
    auction_acceptable_range = np.array([price * 0.85, price]) * quantity

    acceptance_factor = np.floor(max(auction_acceptable_range) / min(auction_acceptable_range) * 10 ** 2) / 10 ** 2
    bids = np.round(np.linspace(min(auction_acceptable_range), max(auction_acceptable_range), bids_total + 1), 2)
    mean = 0
    std_dev = 0.5

    seed = UUID(listing['listing_id']).int % (2 ** 32)

    # Use as numpy seed
    rng = np.random.default_rng(seed)

    noise = rng.normal(mean, std_dev, size=bids.shape)
    noisy_data = bids + noise
    noisy_data = np.floor(noisy_data * 10 ** 2) / 10 ** 2

    return noisy_data[n + 1], acceptance_factor, min(auction_acceptable_range)


if __name__ == "__main__":
    from playhouse.shortcuts import model_to_dict
    from src.entities.db_model import Listing, init_db
    init_db("./marketplace.db")
    listing = Listing.get(Listing.listing_id == "f57c5cfc-118c-4703-b108-6783b385b5d7")
    listing = model_to_dict(listing)

    from src.assets.agent_db import init_db
    init_db("recycler.db")
    print("Listing", listing['material_code'], listing['quantity'])
    print("Buyer quotes", get_quotes(listing, "buyer"))
    print("Seller quotes", get_quotes(listing, "seller"))
    exit()

    data = []
    for i in range(10):
        bid, factor, reserve_price = get_auction_bid({
            "material_code": "nmc_waste",
            "quantity": 220,
            "listing_id": "123e4567-e89b-12d3-a456-426614174000"
        }, i)
        data.append([f"Bid {i + 1}", bid, bid > factor * reserve_price])

    try:
        from tabulate import tabulate
    except ImportError:
        print("WARNING: Tabulate not found.")
        exit()
    print(tabulate(data,
                   headers=['Idx', f"Bids (reserve price: {reserve_price})", f"Accepted (with factor of {factor})"]))
