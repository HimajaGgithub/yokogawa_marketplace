from src.assets.agent_db import Orders, OrderStatus, OrderType, Stock


def handle_listing_delivery(m, listing):
    order = Orders.get_or_none(Orders.listing_id == m['payload']['listing_id'])
    if not order:
        return {
            "instruction": "Ignore delivery message, as no matching order found with a corresponding listing id.",
            "agent_name": "Order Management Agent",
            "listing_object": listing
        }
    order: Orders
    order.status = OrderStatus.ready.value
    order.save()

    if order.order_type == OrderType.procurement.value and order.parent_order_id:
        # Add entry in stock table with parent order id, so it will be marked as consumed when processing
        Stock.create(**{
            "material_code": order.material_code,
            "quantity": order.quantity,
            "units": order.units,
            "status": "reserved",
            "material_type": "raw-material",
            "order_id": order.parent_order_id,
            "run_id": m['run_id'],
        })

        sibling_orders = list(Orders.select().where(
            (Orders.parent_order_id == order.parent_order_id) &
            (Orders.order_type == OrderType.procurement.value)
        ))
        if all(x.status == OrderStatus.ready.value for x in sibling_orders):
            print("All materials procured and ready. Will start processing.")
            parent_order = Orders.get(Orders.order_id == order.parent_order_id)
            parent_order.status = OrderStatus.processing.value
            parent_order.save()
    return {
        "instruction": "Received delivery, tables have been updated. Will process further soon.",
        "agent_name": "Order Processor Agent",
        "listing_object": listing
    }


def handle_new_listing(m, listing, current_user_id):
    if listing['user_id'] == current_user_id:
        existing = Orders.get_or_none(Orders.listing_id == listing['listing_id'])
        if not existing:
            delivery_date = listing['payload'].get("target_date", None)
            if not delivery_date:
                delivery_date = listing['payload'].get("end_date", None)

            order_type = OrderType.procurement.value if listing['listing_type'] == "demand" else OrderType.supply.value
            order_status = OrderStatus.procuring.value if listing[
                                                              'listing_type'] == "demand" else OrderStatus.accepted.value

            Orders.create(**{
                "listing_id": listing['listing_id'],
                "material_code": listing['material_code'],
                "parent_order_id": listing['payload'].get('parent_listing_id', None),
                "quantity": listing['quantity'],
                "selling_price": "",
                "delivery_date": delivery_date,
                "accepted_date": listing['created_at'],
                "order_type": order_type,
                "units": listing['quantity_unit'],
                "status": order_status,
                "run_id": m['run_id'],
            })
        return {
            "instruction": "New listing noted in assets db, so I can keep track of further operations on this listing.",
            "agent_name": "Order Processor Agent",
            "listing_object": listing
        }
    else:
        return {
            "instruction": "Ignore message as I'm not the owner of this listing.",
            "agent_name": "Order Processor Agent",
            "listing_object": listing
        }
