from ..models import Order, TemporalGrant


def create_for_order(order: Order) -> list[TemporalGrant]:
    """Create the chapter-1 grant immediately and schedule chapters 2..N.

    Returns the full list of grants ordered by chapter.order_index.
    The caller (the Stripe webhook) takes the first grant and hands it to
    `whatsapp.send_chapter` for the immediate chapter-1 send.

    Implemented in T004 (cadence scheduler). Until then this raises so that
    fulfillment failures during prototype testing are loud, not silent.
    """
    raise NotImplementedError("T004 cadence scheduler not yet implemented")
