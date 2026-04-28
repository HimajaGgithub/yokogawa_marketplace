function setDPI(canvas, dpi) {
    // Set up CSS size.
    canvas.style.width = canvas.style.width || canvas.width + 'px';
    canvas.style.height = canvas.style.height || canvas.height + 'px';

    // Resize canvas and scale future draws.
    var scaleFactor = dpi / 96;
    canvas.width = Math.ceil(canvas.width * scaleFactor);
    canvas.height = Math.ceil(canvas.height * scaleFactor);
    var ctx = canvas.getContext('2d');
    ctx.scale(scaleFactor, scaleFactor);
}

function set_params(ctx, params) {
    for (const [key, value] of Object.entries(params)) {
        if (typeof ctx[key] === 'function') {
            ctx[key](value);
        } else {
            ctx[key] = value;
        }
    }
}

function draw_circle(ctx, x1, y1, radius, params) {
    ctx.save();
    ctx.beginPath();
    set_params(ctx, params);
    ctx.arc(x1, y1, radius, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = 'black'; // Set the border color
    ctx.lineWidth = 2; // Set the border thickness
    ctx.stroke();
    ctx.restore();
}

function draw_line(ctx, x1, y1, x2, y2, params) {
    ctx.save();
    ctx.beginPath();
    set_params(ctx, params);
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.restore();
}

function draw_slashed_rect(ctx, x, y, width, height, lineColor = 'black', lineWidth = 1, spacing = 10, slantType = '/') {

    // --- 1. Save context and create clipping region ---

    // Save the current state (like stroke color, line width, etc.)
    ctx.save();

    // Create a rectangular path
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, 12);
    // ctx.rect(x, y, width, height);
    // Use this path as a "clipping region". Nothing drawn
    // outside this path will be visible.
    ctx.clip();

    // --- 2. Draw the slanted lines ---

    // Set line properties
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = lineWidth;

    // We draw lines that are guaranteed to be bigger than the
    // rectangle, letting the clip() do the work.

    ctx.beginPath();

    if (slantType === '/') {
        // Forward slash '/'
        // We find the "k" intercept (k = x + y) for the top-left
        // and bottom-right corners to define our loop range.
        const kMin = x + y;
        const kMax = x + width + y + height;

        for (let k = kMin - spacing; k < kMax + spacing; k += spacing) {
            // A line with equation y = -x + k
            // intersects y=0 at x=k and x=0 at y=k.
            ctx.moveTo(k, 0);
            ctx.lineTo(0, k);
        }
    } else {
        // Back slash '\'
        // We find the "k" intercept (k = y - x) for the top-right
        // and bottom-left corners.
        const kMin = y - (x + width);
        const kMax = (y + height) - x;

        for (let k = kMin - spacing; k < kMax + spacing; k += spacing) {
            // A line with equation y = x + k
            // intersects x=0 at y=k.
            // We just need a long line, so we pick a large canvas-relative width.
            const canvasWidth = ctx.canvas.width;
            ctx.moveTo(0, k);
            ctx.lineTo(canvasWidth, k + canvasWidth);
        }
    }

    ctx.stroke();

    // --- 3. Restore context ---

    // Restore the context to its original state,
    // which also removes the clipping region.
    ctx.restore();

    // --- 4. (Optional) Draw the rectangle border ---
    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = lineWidth;
    ctx.roundRect(x, y, width, height, 12);
    // ctx.strokeRect(x, y, width, height);
    ctx.stroke();
}

function draw_angled_text(ctx, text, x, y, angle) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.fillText(text, 0, 0);
    ctx.restore();
}

function draw_angled_text_by_end(ctx, text, x_end, y_end, angle) {
    const textWidth = ctx.measureText(text).width;

    const cosAngle = Math.cos(angle);
    const sinAngle = Math.sin(angle);

    // Calculate the (x, y) START point
    // This is the inverse of the transformation:
    // x_end = x_start + textWidth * cosAngle
    // y_end = y_start + textWidth * sinAngle
    const x_start = x_end - textWidth * cosAngle;
    const y_start = y_end - textWidth * sinAngle;

    draw_angled_text(ctx, text, x_start, y_start, angle);
}

function transform(x, model) {
    let canvas_min = 50, canvas_max = 750;
    let norm = (x - model.scale_min) / (model.scale_max - model.scale_min);
    return norm * (canvas_max - canvas_min) + canvas_min;
}

export {
    draw_line,
    draw_circle,
    draw_slashed_rect,
    transform,
    draw_angled_text,
    draw_angled_text_by_end,
    setDPI
};