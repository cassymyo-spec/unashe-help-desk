from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Asset, AssetLog
from loguru import logger

@receiver(pre_save, sender=Asset)
def asset_pre_save(sender, instance: Asset, **kwargs):
    if not instance._state.adding:  # Only for updates, not creation
        try:
            old_instance = Asset.objects.get(pk=instance.pk)
            instance._old_quantity = old_instance.quantity
        except Asset.DoesNotExist:
            pass

@receiver(post_save, sender=Asset)
def asset_post_save(sender, instance: Asset, created: bool, **kwargs):
    if created and instance.quantity is not None:
        # For new assets
        AssetLog.objects.create(
            asset=instance, 
            quantity=instance.quantity,
            change=instance.quantity  # Initial quantity as change
        )
        logger.success(f"Asset {instance.id} created by {instance.created_by}")
    elif hasattr(instance, '_old_quantity') and instance._old_quantity != instance.quantity:
        # For updates where quantity changed
        change = instance.quantity - instance._old_quantity
        AssetLog.objects.create(
            asset=instance,
            quantity=instance.quantity,
            change=change
        )
        logger.info(f"Asset {instance.id} quantity updated from {instance._old_quantity} to {instance.quantity}")
        del instance._old_quantity