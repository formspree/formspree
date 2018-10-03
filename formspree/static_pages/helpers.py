import glob

from formspree import settings
from formspree.users.models import Plan


PUBLIC_PARAMS = {
    "SERVICE_NAME": settings.SERVICE_NAME,
    "SERVICE_URL": settings.SERVICE_URL,
    "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    "countries": [
        cr.split("/")[-1].split(".")[0].upper()
        for cr in glob.glob("formspree/static/img/countries/*.png")
    ],
    "plans": {
        product_name: {
            "yearly": [
                dict(id=plan_id, **_def)
                for plan_id, _def in Plan.plan_defs.items()
                if _def['product'] == product_name and "yearly" in plan_id
            ][0],
            "monthly": [
                dict(id=plan_id, **_def)
                for plan_id, _def in Plan.plan_defs.items()
                if _def['product'] == product_name and "yearly" not in plan_id
            ][0],
        }
        for product_name in Plan.product_names
    },
}
