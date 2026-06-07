from ..models import TemporalGrant


def send_chapter(grant: TemporalGrant) -> None:
    """Send the WhatsApp message for `grant`'s chapter to grant.user.phone.

    Implemented in T005 (Twilio WhatsApp delivery). Called by the Stripe
    webhook AFTER the fulfillment transaction commits, wrapped in a
    best-effort try/except per Q5 of T003 grilling.
    """
    raise NotImplementedError("T005 Twilio WhatsApp delivery not yet implemented")
