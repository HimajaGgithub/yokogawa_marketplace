import datetime
import math
from datetime import timedelta

from playhouse.shortcuts import model_to_dict

from src.assets.agent_db import Orders, Stock, Config, OrderStatus, OrderType
from src.assets.agents import sales, bidder, negotiator, order_processor
from src.assets.api_utils import get_listing_details, create_listing, generate_listing_preview, logistics_deliver
from src.assets.api_utils import get_llm_response, log, get_all_users
from src.entities.common_schema import MessageType
from src.properties.market_prices import market_prices, unit_quantity, material_yield, stock_buffer
from src.utils.fetch_utils import run_id


def distribute_bucket(material, listing_quantity: float, recyclers):
    result = {k['user_id']: {"days": 0, "quantity": 0} for k in recyclers}

    while listing_quantity > 0:
        for recycler in recyclers:
            daily_production = recycler['daily_production'][material][0]
            if listing_quantity >= daily_production:
                result[recycler['user_id']]["quantity"] += daily_production
                result[recycler['user_id']]['days'] += 1
                listing_quantity -= daily_production
            else:
                result[recycler['user_id']]['quantity'] += listing_quantity
                result[recycler['user_id']]['days'] += 1
                listing_quantity = 0  # remainder used up

    return result


def check_stock(order: Orders, listing, daily_production):
    result = {}
    analysis = {}

    if order.material_code not in daily_production:
        return {}, {}

    for material, unit_quantity_required, unit, quality, category in unit_quantity[order.material_code].values():
        required_qty = unit_quantity_required * order.quantity
        print("LOOKING FOR EXISTING STOCK", material, required_qty, unit, quality, category)

        # Try to fulfill from existing surplus stock
        surplus = (
            Stock.select()
            .where(
                (Stock.material_code == material)
                & (Stock.quantity >= required_qty)
                & (Stock.material_type == "surplus")
                & (Stock.status == "available")
            )
            .get_or_none()
        )

        if surplus:
            print("FOUND matching surplus")

            difference = surplus.quantity - required_qty
            surplus.quantity = required_qty
            surplus.order_id = order.order_id
            surplus.status = "reserved"
            surplus.save()

            analysis[material] = (
                f"Found {required_qty} {unit} of {surplus.material_code} in inventory."
            )

            # Save new entry for leftover stock
            if difference > 0:
                Stock.create(
                    material_code=material,
                    quantity=difference,
                    units=unit,
                    status="available",
                    material_quality=quality,
                    category=category,
                    material_type="surplus",
                )
            continue  # Skip to next material if stock was satisfied

        # Build requirement analysis
        steps = [
            f"* {order.material_code} requires {unit_quantity_required} {unit} of {material} per unit.",
            f"* Order with quantity {order.quantity} {order.units}, "
            f"requires {unit_quantity_required} × {order.quantity} = {round(required_qty, 3)}",
        ]

        # Apply recycled content adjustment - CHANGED LOGIC HERE
        recycled_materials_percent = listing["payload"].get("recycled_materials_percent", 20)
        if material in material_yield and recycled_materials_percent:
            # Calculate only the recycled portion instead of adding to total
            recycled_qty = required_qty * (recycled_materials_percent / 100)
            steps += [
                f"* Target recycled content is {recycled_materials_percent}%.",
                f"* Recycled portion needed: {required_qty} × ({recycled_materials_percent} / 100) = {round(recycled_qty, 3)}",
            ]
            required_qty = recycled_qty  # Only process the recycled portion

        # Apply yield factor
        if material in material_yield:
            yield_factor = material_yield[material]
            steps += [
                f"* Yield of {material} is {yield_factor * 100}%.",
                f"* Adjusted order quantity: {round(required_qty, 3)} / {yield_factor} = {round(required_qty / yield_factor, 3)}",
            ]
            required_qty /= yield_factor

        # Apply buffer
        if material in stock_buffer:
            buffer_factor = stock_buffer[material]
            buffer_pct = (buffer_factor - 1) * 100
            steps += [
                f"* Keeping a buffer of {buffer_pct}%, adjusted quantity = {round(required_qty * buffer_factor, 3)} {unit}",
            ]
            required_qty *= buffer_factor

        # Rounding rules
        if unit == "packs":
            rounded_qty = math.ceil(required_qty / 100) * 100
        elif unit == "MWh":
            rounded_qty = math.ceil(required_qty)
            # rounded_qty = math.ceil(required_qty / 10) * 10
        elif unit == "tons":
            rounded_qty = math.ceil(required_qty)
        else:
            raise ValueError(f"Invalid unit: {unit} in unit_quantity.")

        steps.append(f"* Rounding up {round(required_qty, 3)}, we get {rounded_qty} {unit}.")

        result[material] = (material, rounded_qty, unit, quality, category, "")
        analysis[material] = "\n".join(steps)

    return result, analysis


def check_for_supply_in_stock(location):
    # supply materials sitting in warehouse for more than 90 days
    idle_stock = Stock.select().where(
        (Stock.material_type == "surplus") &
        (Stock.status == "available") &
        (Stock.created_at < datetime.datetime.now(datetime.UTC) - timedelta(days=90))
    )

    for item in idle_stock:
        run_id.set(item.run_id)
        if item.material_code not in market_prices:
            continue
        print("IDLE stock", model_to_dict(item))
        item: Stock
        quality_key, quality_value = item.material_quality.split()
        end_date = datetime.datetime.now(datetime.UTC).date() + datetime.timedelta(days=4)
        supply_message = f"""
            item_name (title): "Sell {item.material_code} {item.quantity} {item.units} around {location}, by {end_date} up for auction.",
            category: {item.category},
            listing_type: supply,
            material_code: {item.material_code},
            quantity: {item.quantity},
            quantity_unit: {item.units},
            location: {location}
            payload: {{
                    "transaction_type":"auction",
                    "{quality_key}":{quality_value},
                    "end_date": {end_date},
                    "reserve_price":{market_prices[item.material_code] * item.quantity},
                    }},
        """.strip()
        print("Supply message", supply_message)

        x = generate_listing_preview(supply_message)
        preview = x['response']
        res = get_llm_response("", {
            "instruction": f"I found this item in my inventory for a long time, placing it in the marketplace {preview}",
            "function": "create_listing",
            "args": preview
        })
        preview.update(res)
        listing = create_listing(preview)

        # todo: maybe item status must be "for sale"
        item.status = "reserved"
        item.save()
        log({
            "instruction": f"Created supply listing {listing['listing_id']} for idle stock {item.material_code}.",
            "agent_name": "Stock Manager Agent",
            "tag": "internal", **res
        })


def check_for_large_orders(location):
    accepted_orders = Orders.select().where(
        (Orders.status == OrderStatus.accepted.value) &
        (Orders.order_type == "supply")
    )

    for order in accepted_orders:
        all_users = get_all_users()
        recyclers = [x for x in all_users if x['biz_type'] == "recycler"]

        if not order.delivery_date:
            continue
        run_id.set(order.run_id)
        order: Orders
        if order.listing_id:
            listing = get_listing_details(order.listing_id)
        else:
            print("WARNING: listing id not found in check for large orders.")
            continue

        buckets = distribute_bucket(listing['material_code'], listing['quantity'], recyclers)
        material = listing['material_code']
        for target, quantities in buckets.items():
            quantity = quantities['quantity']
            unit = listing['quantity_unit']
            category = listing['category']
            print("Order delivery date", order.delivery_date, type(order.delivery_date))
            delivery_date = order.delivery_date
            if isinstance(delivery_date, str):
                delivery_date = datetime.datetime.fromisoformat(order.delivery_date)
            procurement_deadline = delivery_date - timedelta(days=1)
            demand_message = f"""
                    item_name (title): "Buy {material} {quantity} {unit} around {location}, by {procurement_deadline} up for negotiations",
                    category: {category},
                    listing_type: demand,
                    material_code: {material},
                    quantity: {quantity},
                    quantity_unit: {unit},
                    location: {location}
                    payload: {{"purity": {listing['payload'].get("purity")} }},
                    target_date: {procurement_deadline}
                """.strip()
            print("Demand message", demand_message)

            x = generate_listing_preview(demand_message)
            preview = x['response']
            if order.listing_id:
                preview['payload']['parent_listing_id'] = order.listing_id

            res = get_llm_response("", {
                "instruction": f"Creating listings to procure materials from recyclers",
                "function": "create_listing",
                "args": preview
            })
            print("Demand LLM RES", res)
            preview.update(res)

            preview['target_user'] = target
            new_listing = create_listing(preview)
            print("GOT NEW LISTING", new_listing)

            Orders.create(**{
                "listing_id": new_listing['listing_id'],
                "material_code": material,
                "parent_order_id": order.order_id,
                "quantity": quantity,
                "selling_price": "",
                "delivery_date": procurement_deadline,
                "accepted_date": order.accepted_date,
                "order_type": OrderType.procurement.value,
                "units": unit,
                "status": OrderStatus.procuring.value,
                "run_id": run_id.get(),
            })

            log({
                "instruction": f"Procuring {material} for order {order.order_id}.",
                "agent_name": "Order Processor Agent",
                "tag": "internal", **res
            })
        order.status = "procuring"
        order.save()


def check_for_accepted_orders(location):
    daily_production = Config.get(Config.key == "daily_production").value

    accepted_orders = Orders.select().where(
        (Orders.status == OrderStatus.accepted.value) &
        (Orders.order_type == "supply")
    )

    for order in accepted_orders:
        if not order.delivery_date:
            continue
        run_id.set(order.run_id)
        order: Orders
        if order.listing_id:
            listing = get_listing_details(order.listing_id)
        else:
            listing = {"payload": {"recycled_materials_percent": 20}}

        to_procure, analysis = check_stock(order, listing, daily_production)
        print("Stock Analysis")
        for k, v in analysis.items():
            print(k, ":")
            print(v)
        if to_procure:
            print("TO PROCURE", to_procure)

            for (material, quantity, unit, quality, category, _target) in to_procure.values():
                # make entry in stocks table
                # create listing

                # daily_production[material] will be (quantity, unit),
                # so I'm doing daily_production[material][0]
                days_for_production = math.ceil(order.quantity / daily_production[order.material_code][0])
                delivery_date = order.delivery_date
                if isinstance(delivery_date, str):
                    delivery_date = datetime.datetime.fromisoformat(delivery_date)
                procurement_deadline = (delivery_date - timedelta(days=math.ceil(days_for_production))).isoformat()
                quality_param, quality_number = quality.split()

                demand_message = f"""
                    item_name (title): "Buy {material} {quantity} {unit} around {location}, by {procurement_deadline} up for negotiations",
                    category: {category},
                    listing_type: demand,
                    material_code: {material},
                    quantity: {quantity},
                    quantity_unit: {unit},
                    location: {location}
                    payload: {{"{quality_param}":{quality_number}}},
                    target_date: {procurement_deadline}
                """.strip()
                print("Demand message", demand_message)

                x = generate_listing_preview(demand_message)
                preview = x['response']
                if order.listing_id:
                    preview['payload']['parent_listing_id'] = order.listing_id

                res = get_llm_response("", {
                    "instruction": f"Use this analysis as the anchor to generate the response:\n{analysis[material]}",
                    "function": "create_listing",
                    "args": preview
                })
                print("Demand LLM RES", res)
                preview.update(res)

                listing = create_listing(preview)
                print("GOT LISTING", listing)

                Orders.create(**{
                    "listing_id": listing['listing_id'],
                    "material_code": material,
                    "parent_order_id": order.order_id,
                    "quantity": quantity,
                    "selling_price": "",
                    "delivery_date": procurement_deadline,
                    "accepted_date": order.accepted_date,
                    "order_type": OrderType.procurement.value,
                    "units": unit,
                    # once logistics sends {"listing_id":"", "status": "delivered"}
                    # mark this status as OrderStatus.delivered.
                    "status": OrderStatus.procuring.value,
                    "run_id": run_id.get(),
                })

                log({
                    "instruction": f"Procuring {material} for order {order.order_id}.",
                    "agent_name": "Order Processor Agent",
                    "tag": "internal", **res
                })
            order.status = "procuring"
            order.save()
        else:
            order.status = "processing"
            order.save()
            log({
                "instruction": f"Order {order.order_id} has been accepted and all materials are in stock. "
                               f"Will process the order soon.",
                "agent_name": "Order Processor Agent",
                "tag": "internal"
            })


def check_for_processing_orders():
    # daily_production = Config.get(Config.key == "daily_production").value
    processing_orders = Orders.select().where(
        (Orders.status == OrderStatus.processing.value) &
        (Orders.order_type == OrderType.supply.value)
    )
    for order in processing_orders:
        print("ORDER RUN ID", order.run_id)
        run_id.set(order.run_id)
        reserved_stock = Stock.select().where(Stock.order_id == order.order_id)
        for stock in reserved_stock:
            stock.status = "consumed"
            stock.save()

        # number_of_days = math.ceil(order.quantity / daily_production[order.material_code][0])
        # last_entry = Calendar.select().order_by(Calendar.date.desc()).get_or_none()
        # if last_entry:
        #     latest_date = last_entry.date + timedelta(days=1)
        # else:
        #     latest_date = order.accepted_date

        # We don't need this level of modeling, as the simulations will
        # stop working because all the agents are occupied. So, I'm not creating
        # the calendar occupied entries.
        # for i in range(number_of_days):
        #     Calendar.create(**{
        #         "listing_id": order.listing_id,
        #         "date": latest_date + timedelta(days=i),
        #         "status": "occupied",
        #         "run_id": order.run_id
        #     })

        Stock.create(**{
            "material_code": order.material_code,
            "quantity": order.quantity,
            "units": order.units,
            "status": "reserved",
            "material_type": "finished-product",
            "order_id": order.order_id,
            "run_id": run_id.get(),
        })
        log({
            "instruction": f"Order {order.order_id} has been processed and is ready for delivery.",
            "agent_name": "Order Processor Agent",
            "tag": "internal"
        })
        order.status = OrderStatus.ready.value
        order.save()


def check_for_ready_orders():
    ready_orders = Orders.select().where(
        (Orders.status == OrderStatus.ready.value) &
        (Orders.order_type == OrderType.supply.value)
    )
    for order in ready_orders:
        if not order.listing_id:
            continue

        run_id.set(order.run_id)

        listing = get_listing_details(order.listing_id)
        if listing['status'] != "accepted":
            print("listing status is ", listing['status'], "continuing")
            # This check ensures that you don't hit delivery on
            # a listing before the auction closes.
            # You should be hitting logistics only on accepted listings.
            continue

        # inform logistics
        res = get_llm_response("", {
            "instruction": "Send the ready product via logistics.",
            "function": "logistics_deliver",
            "args": {"listing_id": order.listing_id}
        })

        if order.listing_id:
            print("Found ready supply order, informing logistics", order.listing_id)
            logistics_deliver(order.listing_id, **res)
        order.status = OrderStatus.delivered.value
        order.save()
        log({
            "instruction": f"Order {order.order_id} is ready and sent via logistics.",
            "agent_name": "Order Processor Agent",
            "tag": "marketplace", **res
        })


async def inference_engine(m, current_user_id, current_user_profile):
    run_id.set(m['run_id'])
    daily_production = Config.get(Config.key == "daily_production").value
    materials_of_interest = Config.get(Config.key == "materials_of_interest").value

    listing = get_listing_details(m['listing_id'])

    if m['message_type'] in [MessageType.market_listing_announcement.value, MessageType.takeover.value]:
        return sales.handle_market_listing_announcement(
            m, listing, current_user_id, daily_production,
            materials_of_interest, current_user_profile
        )
    elif m['message_type'] == MessageType.auction_new_highest_bid.value:
        return bidder.handle_new_highest_bid(m, listing, current_user_id, materials_of_interest)
    elif m['message_type'] == MessageType.negotiation_offer.value:
        return negotiator.handle_offer(m, listing, current_user_id)
    elif m['message_type'] in [MessageType.negotiation_counter_offer.value, MessageType.negotiation_reject.value]:
        return negotiator.handle_reject_or_counter(m, listing, current_user_id)
    elif m['message_type'] == MessageType.negotiation_accept.value:
        return negotiator.handle_accept(m, listing)
    elif m['message_type'] == MessageType.auction_winner.value:
        return bidder.handle_winner(m, listing)
    elif m['message_type'] == MessageType.auction_closed.value:
        return bidder.handle_closed(m, listing)
    elif m['message_type'] == MessageType.listing_delivery.value:
        return order_processor.handle_listing_delivery(m, listing)
    elif m['message_type'] == MessageType.new_listing.value:
        return order_processor.handle_new_listing(m, listing, current_user_id)
