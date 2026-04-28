import { setDPI, draw_line } from "/static/canvas_utils.js";
import { render } from "/static/model.js";

function show_model_fields(s) {
    let fieldset = s.closest("fieldset");
    fieldset.querySelectorAll(".model").forEach((m) => { m.classList.add("hide") });
    fieldset.querySelector(`.${s.value}`).classList.replace("hide", "show");
}

window.onload = function () {
    const buyer_template = document.getElementById('buyer-model-template');
    const seller_template = document.getElementById('seller-model-template');

    const buyer_fields = buyer_template.content.cloneNode(true);
    let buyer_model_select = buyer_fields.querySelector('select[name="buyer_scheme"]');
    buyer_model_select.querySelector('option[value="price"]').disabled = true;
    buyer_model_select.querySelector('option[value="margin"]').disabled = true;
    buyer_model_select.querySelector('option[value="distribution"]').selected = true;

    const seller_fields = seller_template.content.cloneNode(true);
    let seller_model_select = seller_fields.querySelector('select[name="seller_scheme"]');
    seller_model_select.querySelector('option[value="price"]').disabled = true;
    seller_model_select.querySelector('option[value="margin"]').disabled = true;
    seller_model_select.querySelector('option[value="distribution"]').selected = true;

    let default_form = document.querySelector("#default-negotiation-model");
    default_form.insertBefore(buyer_fields, default_form.querySelector('input[type="submit"]'));
    default_form.insertBefore(seller_fields, default_form.querySelector('input[type="submit"]'));

    default_form.addEventListener("submit", (e) => {
        e.preventDefault();
        let model = render(null, default_form);
        fetch("/negotiation", {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(model)
        });
    });

    let controls_form = document.querySelector("#controls");
    const buyer_controls = buyer_template.content.cloneNode(true);
    buyer_controls.querySelector('option[value="distribution"]').selected = true;

    const seller_controls = seller_template.content.cloneNode(true);
    seller_controls.querySelector('option[value="distribution"]').selected = true;
    controls_form.insertBefore(buyer_controls, controls_form.childNodes[2]);
    controls_form.insertBefore(seller_controls, controls_form.childNodes[3]);

    document.querySelectorAll(".scheme-selector").forEach((s) => {
        let fieldset = s.closest("fieldset");
        fieldset.querySelectorAll(".model").forEach((m) => { m.classList.add("hide"); });
        s.addEventListener("change", (e) => { show_model_fields(e.target) });
        show_model_fields(s);
    });

    const canvas = document.querySelector('canvas');
    setDPI(canvas, 144);
    const ctx = canvas.getContext('2d');

    let form = document.querySelector("#controls");
    console.log(form);
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        render(ctx, form);
    });
    render(ctx, form);
};
