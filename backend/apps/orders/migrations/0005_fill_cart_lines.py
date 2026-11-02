"""Existing orders had one product and a quantity: give each one its line, container count and total."""
from django.db import migrations


def forwards(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")
    for o in Order.objects.filter(items__isnull=True).iterator():
        OrderItem.objects.create(order=o, product_id=o.product_id, quantity=o.quantity, unit_price=o.unit_price)
        Order.objects.filter(pk=o.pk).update(containers=o.quantity, total=o.unit_price * o.quantity)


class Migration(migrations.Migration):
    dependencies = [("orders", "0004_cart"), ("inventory", "0004_cart")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
