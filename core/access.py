from .models import Order, TemporalGrant

def user_has_access_to(user, chapter) -> bool:
    """
    True iff a successful Order exists for (user, chapter.book)
    AND that user's TemporalGrant for chapter is unlocked (now >= unlock_at).
    """
    if not user.is_authenticated:
        return False
    
    # 1. Check if an order exists for the book this chapter belongs to
    has_order = Order.objects.filter(user=user, book=chapter.book).exists()
    if not has_order:
        return False
    
    # 2. Check if a TemporalGrant exists for this user and shard, and it's valid
    # (unlocked + not expired + views left)
    grant = TemporalGrant.objects.filter(
        user=user, 
        shard=chapter.shard
    ).first()
    
    if not grant:
        return False
        
    return grant.is_valid()
