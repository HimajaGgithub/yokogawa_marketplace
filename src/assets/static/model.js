import {
    draw_line,
    draw_angled_text,
    draw_angled_text_by_end,
    draw_circle,
    transform,
    draw_slashed_rect,

} from "./canvas_utils.js";

function get_numbers(dist) {
    let res = [];
    dist.split(",").forEach((x) => {
        let str_repr = x.trim();
        res.push(parseFloat(str_repr));
    })
    return res;
}

function interpolate(a, b, p) {
    let t = p / 100;
    return a + t * (b - a);
}

function convert_form_to_model(form) {
    let data = Object.fromEntries(new FormData(form));
    console.log("form data", data);
    let model = {
        buyer_scheme: data.buyer_scheme,
        seller_scheme: data.seller_scheme,
    }

    if (data.scale_min) {
        model.scale_min = parseFloat(data.scale_min);
    }
    if (data.scale_max) {
        model.scale_max = parseFloat(data.scale_max);
    }
    if (data.market_price) {
        model.market_price = parseFloat(data.market_price);
    }

    if (model.buyer_scheme == "price") {
        model.buyer_prices = get_numbers(data.buyer_prices);
        model.buyer_budget_min = Math.min(...data.buyer_prices);
        model.buyer_budget_max = Math.max(...data.buyer_prices);

    } else if (model.buyer_scheme == "margin") {
        model.buyer_margins = get_numbers(data.buyer_margins);
        if (model.market_price) {
            model.buyer_budget_min = model.market_price * Math.min(...model.buyer_margins) / 100;
            model.buyer_budget_max = model.market_price * Math.max(...model.buyer_margins) / 100;
            model.buyer_prices = [];
            model.buyer_margins.forEach((x) => {
                let price = (data.market_price * x / 100);
                model.buyer_prices.push(price);
            });
        }


    } else if (model.buyer_scheme == "distribution") {
        model.buyer_margin_min = parseFloat(data.buyer_margin_min);
        model.buyer_margin_max = parseFloat(data.buyer_margin_max);
        model.buyer_distribution = get_numbers(data.buyer_distribution);
        if (model.market_price) {
            model.buyer_budget_min = model.market_price * model.buyer_margin_min / 100;
            model.buyer_budget_max = model.market_price * model.buyer_margin_max / 100;
            model.buyer_prices = [];
            model.buyer_distribution.forEach((x) => {
                let price = interpolate(model.buyer_budget_min, model.buyer_budget_max, x);
                console.log("Interpolate", model.buyer_budget_min, model.buyer_budget_max, x, price);
                model.buyer_prices.push(price);
            });
        }
    }

    if (model.seller_scheme == "price") {
        model.seller_prices = get_numbers(data.seller_prices);
        model.seller_budget_min = Math.min(...data.seller_prices);
        model.seller_budget_max = Math.max(...data.seller_prices);

    } else if (model.seller_scheme == "margin") {
        model.seller_margins = get_numbers(data.seller_margins);
        if (model.market_price) {
            model.seller_budget_min = model.market_price * Math.min(...model.seller_margins) / 100;
            model.seller_budget_max = model.market_price * Math.max(...model.seller_margins) / 100;
            model.seller_prices = [];
            model.seller_margins.forEach((x) => {
                let price = (data.market_price * x / 100);
                model.seller_prices.push(price);
            });
        }

    } else if (model.seller_scheme == "distribution") {
        model.seller_margin_min = parseFloat(data.seller_margin_min);
        model.seller_margin_max = parseFloat(data.seller_margin_max);
        model.seller_distribution = get_numbers(data.seller_distribution);
        if (model.market_price) {
            model.seller_budget_min = model.market_price * model.seller_margin_min / 100;
            model.seller_budget_max = model.market_price * model.seller_margin_max / 100;
            model.seller_prices = [];
            model.seller_distribution.forEach((x) => {
                let price = interpolate(model.seller_budget_min, model.seller_budget_max, x);
                console.log("Interpolate", model.seller_budget_min, model.seller_budget_max, x, price);
                model.seller_prices.push(price);
            });
        }
    }

    return model;
}


function render(ctx, form) {
    let model = convert_form_to_model(form);
    console.log("Model", JSON.stringify(model, null, 4));
    if (!ctx) {
        return model;
    }

    let min_x = 50, max_x = 750;
    let seller_y = 150, buyer_y = 400;

    ctx.clearRect(0, 0, 800, 600);
    draw_line(ctx, min_x, seller_y, max_x, seller_y, { lineWidth: 1, strokeStyle: "black", lineCap: "round" })
    draw_line(ctx, min_x, buyer_y, max_x, buyer_y, { lineWidth: 1, strokeStyle: "black", lineCap: "round" })
    let market_x = transform(model.market_price, model);
    draw_line(ctx, market_x, 50, market_x, 550, { lineWidth: 1, strokeStyle: "black", lineCap: "round", "setLineDash": [5, 5] })

    ctx.font = "18px sans-serif";
    ctx.fillText("Seller", 30, 140);
    ctx.fillText("Buyer", 30, 424);
    ctx.fillText("Market price", market_x - 30, 570);

    if (model.buyer_budget_max > model.seller_budget_min) {
        let val = interpolate(model.seller_budget_min, model.seller_budget_max, 0);
        let left = transform(val, model);
        val = interpolate(model.buyer_budget_min, model.buyer_budget_max, 100);
        let right = transform(val, model);

        draw_slashed_rect(ctx, left, seller_y, right - left, buyer_y - seller_y);
    }
    ctx.font = "10px sans-serif";
    model.seller_prices.forEach((val) => {
        let x = transform(val, model);
        console.log("seller val, x", val, x);
        let color = "orange";
        if (val <= model.buyer_budget_max) {
            color = "green";
        }
        draw_circle(ctx, x, seller_y, 8, { fillStyle: color });
        draw_angled_text(ctx, String(val / 1000) + "k", x - 4, seller_y - 12, -0.6);
    });

    model.buyer_prices.forEach((val) => {
        let x = transform(val, model);
        console.log("buyer val, x", val, x);
        let color = "orange";
        if (val >= model.seller_budget_min) {
            color = "green";
        }
        draw_circle(ctx, x, buyer_y, 8, { fillStyle: color });
        draw_angled_text_by_end(ctx, String(val / 1000) + "k", x - 2, buyer_y + 14, -0.7);
    });

    // for (const [k, v] of Object.entries(model)) {
    //     let field = form.querySelector(`input[name="${k}"]`);
    //     if (!field){continue;}
    //     if (v instanceof Number) {
    //         field.value = String(v);
    //     } else if (Array.isArray(v)) {
    //         field.value = v.join(", ");
    //     } else {
    //         field.value = v;
    //     }
    // }
    return model;

}

export {
    render
}