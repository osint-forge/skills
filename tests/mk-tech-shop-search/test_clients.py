#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["requests>=2.28", "beautifulsoup4>=4.11"]
# ///
"""Focused offline tests for the real shop-client parsers and read-only windows."""

import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

SKILL = os.environ.get("MKSHOP_SKILL_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "skills",
    "mk-tech-shop-search",
)
STORES = os.path.join(SKILL, "scripts", "stores")
if STORES not in sys.path:
    sys.path.insert(0, STORES)

import ananas as ana  # noqa: E402
import anhoch as anh  # noqa: E402
import neksio as nks  # noqa: E402
import neptun as nep  # noqa: E402
import setec as sec  # noqa: E402

fails = 0


def check(name, condition, info=""):
    global fails
    print(("ok   " if condition else "FAIL ") + name + ("" if condition else f"  [{info}]"))
    if not condition:
        fails += 1


# Date/time normalisation shared by the clients, including the no-tzdata fallback.
ISO_CASES = [
    ("2026-10-15T23:00", "2026-10-15T23:00:00+02:00"),
    ("2026-10-30T23:59:59", "2026-10-30T23:59:59+01:00"),
    ("/Date(1791151140000)/", "2026-10-04T23:59:00+02:00"),
    ("/Date(-62135596800000)/", None),
    ("0001-01-01T00:00:00", None),
    ("2026-12-31T22:59:00.000Z", "2026-12-31T23:59:00+01:00"),
    ("2026-10-31", "2026-10-31T23:59:59+01:00"),
    ("4.10.2026.", "2026-10-04T23:59:59+02:00"),
    ("04.10.2026 15:30", "2026-10-04T15:30:00+02:00"),
    (1791151140, "2026-10-04T23:59:00+02:00"),
    ("", None),
    (None, None),
    ("garbage", None),
    ("2026-02-30", None),
]
for module in (ana, anh, nep, sec):
    bad = [(value, want, module.skopje_iso(value)) for value, want in ISO_CASES if module.skopje_iso(value) != want]
    check(f"{module.__name__}: skopje_iso handles every shop format", not bad, bad)

saved_zoneinfo = sys.modules.get("zoneinfo")
sys.modules["zoneinfo"] = None
try:
    bad = [(value, want, ana.skopje_iso(value)) for value, want in ISO_CASES if ana.skopje_iso(value) != want]
    check("skopje_iso: EU DST fallback without zoneinfo", not bad, bad)
finally:
    if saved_zoneinfo is None:
        del sys.modules["zoneinfo"]
    else:
        sys.modules["zoneinfo"] = saved_zoneinfo
check(
    "skopje_iso: identical helper in every client",
    len({module.skopje_iso.__code__.co_code for module in (ana, anh, nep, sec)}) == 1,
)

# Ananas: sale windows come from the Algolia hit or the detail payload.
ananas = object.__new__(ana.Ananas)
hit = {
    "objectID": "5418872",
    "price": 6690.0,
    "basePrice": 13000.0,
    "onSale": True,
    "discountType": "SALE",
    "merchant": {"id": 776, "displayName": "AНАНАС ШОП"},
    "product": {"name": "VILLAGER VHW 140", "slug": "v"},
}
check(
    "ananas listing: sale window from the index",
    ananas.hit_to_record(dict(hit, discountEndTime="2099-10-04T23:00:00.000000")).get("price_valid_until")
    == "2099-10-04T23:00:00+02:00",
)
check(
    "ananas listing: sale hit without a window -> key absent",
    "price_valid_until" not in ananas.hit_to_record(dict(hit)),
)
check(
    "ananas listing: stale window on a sale hit -> null",
    ananas.hit_to_record(dict(hit, onSale=False, discountEndTime="2099-10-05T15:00:00.000000")).get(
        "price_valid_until", "ABSENT"
    )
    is None,
)
check(
    "ananas listing: undiscounted price -> null",
    ananas.hit_to_record(dict(hit, price=13000.0, onSale=False)).get("price_valid_until", "ABSENT") is None,
)
pv = {"discountType": "SALE", "dateFrom": "2026-10-01T00:00", "dateTo": "2099-10-30T23:59:59"}
check("ananas detail: priceV2.dateTo", ana.Ananas.sale_valid_until(pv, 8490, 13890) == "2099-10-30T23:59:59+01:00")
check(
    "ananas detail: lapsed window kept",
    ana.Ananas.sale_valid_until(dict(pv, dateTo="2026-10-02T23:59:59"), 2974, 3499) == "2026-10-02T23:59:59+02:00",
)
check(
    "ananas detail: standing discount -> null",
    ana.Ananas.sale_valid_until({"discountType": None, "dateTo": None}, 2690, 4290) is None,
)
check("ananas detail: no markdown -> null", ana.Ananas.sale_valid_until(pv, 4290, 4290) is None)

# Neptun: member and online price windows come from named promotions.
neptun = object.__new__(nep.Neptun)
P = {
    "Id": 7,
    "Title": "TV X (UE55X1)",
    "ShortTitle": "TV X",
    "Url": "tv-x",
    "RegularPrice": 9999,
    "DiscountPrice": 7999,
    "DiscountPriceType": 3,
}
HW = {
    "Id": 4343,
    "PromotionName": "M20260395 | HAPPY WEEKS #2 21.09-04.10.2026",
    "ValidFrom": "/Date(1789941600000)/",
    "ValidTo": "/Date(4083947940000)/",
}
WAR = {
    "Id": -3245,
    "PromotionName": "Samsung TV 2+3YW",
    "ValidFrom": "/Date(1787566320000)/",
    "ValidTo": "/Date(4102441140000)/",
}
ND = dict(P, DiscountPriceName="haPPy", DiscountPriceType=3, PromotionId=4343, WebPromotionId=0, Promotions=[WAR, HW])
detail = neptun.detail_record(dict(ND), [], "7")
check(
    "neptun detail: member window = PromotionId ValidTo",
    detail.get("member_price_valid_until") == "2099-05-31T23:59:00+02:00"
    and detail.get("price_valid_until", "ABSENT") is None,
    detail,
)
check(
    "neptun detail: every promotion window in extra",
    [w["id"] for w in detail["extra"]["promotion_windows"]] == [-3245, 4343],
    detail["extra"],
)
check(
    "neptun detail: unnamed promotion -> member window left out",
    neptun.detail_record(dict(ND, PromotionId=0), [], "7").get("member_price_valid_until", "ABSENT") == "ABSENT",
)
check(
    "neptun detail: no member price -> no member window",
    "member_price_valid_until" not in neptun.detail_record(dict(P, DiscountPrice=0, DiscountPriceType=0), [], "7"),
)
check(
    "neptun detail: online price window = WebPromotionId ValidTo",
    neptun.detail_record(
        dict(
            P,
            DiscountPrice=0,
            DiscountPriceType=0,
            WebshopDiscountPrice=8999,
            WebPromotionId=77,
            Promotions=[dict(HW, Id=77)],
        ),
        [],
        "7",
    ).get("price_valid_until")
    == "2099-05-31T23:59:00+02:00",
)
check(
    "neptun listing: no invented member window",
    "member_price_valid_until" not in neptun.listing_record(dict(P, DiscountPriceName="HaPPy")),
)

# Setec: price-list windows.
WEB = {
    "price_list": {"id": "plist_WEB", "title": "Web Prices", "role": "club", "starts_at": None, "ends_at": None},
    "prices": {"amount": "1409"},
}
PROMO = {
    "price_list": {
        "id": "plist_PROMO",
        "title": "Promo",
        "role": "promo",
        "starts_at": "2099-10-01T00:00:00.000Z",
        "ends_at": "2099-10-31T22:59:59.000Z",
    },
    "prices": {"amount": "999"},
}
check("setec: standing price list -> null", sec.price_list_window([WEB], 1409, "plist_WEB") is None)
check(
    "setec: promo list by id -> ends_at",
    sec.price_list_window([WEB, PROMO], 999, "plist_PROMO") == "2099-10-31T23:59:59+01:00",
)
check(
    "setec: detail API matches list by amount",
    sec.price_list_window(
        [{k: (dict(v, id=None) if k == "price_list" else v) for k, v in item.items()} for item in (WEB, PROMO)], 999
    )
    == "2099-10-31T23:59:59+01:00",
)
check(
    "setec: ambiguous amount -> unknown",
    sec.price_list_window([PROMO, {"price_list": {"ends_at": "2099-11-30T22:59:59Z"}, "prices": {"amount": 999}}], 999)
    is sec.NO_WINDOW,
)
check(
    "setec: listing carries its window",
    sec.record_from_hit(
        {
            "id": "prod_1",
            "title": "X",
            "handle": "x",
            "price_lists": [WEB, PROMO],
            "total_web_quantity": 5,
            "variants": [
                {
                    "calculated_price": {
                        "calculated_amount": 999,
                        "original_amount": 1499,
                        "calculated_price": {"price_list_id": "plist_PROMO"},
                    }
                }
            ],
        },
        3,
    ).get("price_valid_until")
    == "2099-10-31T23:59:59+01:00",
)

# Anhoch: FleetCart specials end at the end of the named Skopje day.
anhoch = object.__new__(anh.Anhoch)
amount = lambda value: {"amount": f"{value}.0000"}  # noqa: E731
row = {
    "id": 1,
    "name": "JBL X",
    "slug": "jbl-x",
    "price": amount(2490),
    "selling_price": amount(1990),
    "special_price": amount(1990),
    "special_price_type": None,
    "special_price_start": None,
    "special_price_end": None,
    "is_in_stock": True,
    "qty": 10,
    "manage_stock": True,
}
record = lambda **kw: anhoch.listing_record(dict(row, **kw))  # noqa: E731
check(
    "anhoch: open-ended special -> null",
    record()["price_valid_until"] is None and record()["regular_price_mkd"] == 2490,
)
check(
    "anhoch: special end -> end of Skopje day",
    record(special_price_end="2099-10-31")["price_valid_until"] == "2099-10-31T23:59:59+01:00",
)
check(
    "anhoch: UTC local midnight -> same day",
    record(special_price_end="2099-07-15 00:00:00")["price_valid_until"] == "2099-07-15T23:59:59+02:00",
)
check(
    "anhoch: standing price ignores end",
    record(selling_price=amount(2490), special_price=None, special_price_end="2099-10-31")["price_valid_until"] is None,
)
check(
    "anhoch: mismatched charged price -> unknown",
    "price_valid_until" not in record(special_price=amount(2100), special_price_end="2099-07-15"),
)

# Neksio: a sale price does not imply a window.
neksio = object.__new__(nks.Neksio)
check(
    "neksio: sale price has no invented window",
    "price_valid_until"
    not in neksio.listing_record(
        {
            "productId": 1,
            "productName": "X",
            "productCode": "1",
            "priceWTax": 3990,
            "old_PriceWTax": "4.720 ден.",
            "isOnSale": True,
            "quantity": 3,
            "category": "C",
            "manufacturer": "M",
            "barCode": "4895213700344",
            "futureDocumentDate": None,
        }
    ),
)

# Windows pipes default to a legacy code page; every client must still emit UTF-8 JSON.
bad = []
for client in sorted(os.listdir(STORES)):
    if not client.endswith(".py"):
        continue
    args = [sys.executable, "-B", os.path.join(STORES, client)]
    if client == "gjirafa.py":
        args += ["--site", "zirafamall"]
    args += ["info"]
    result = subprocess.run(
        args,
        capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1"),
        timeout=60,
    )
    try:
        json.loads(result.stdout.decode("utf-8"))
        if result.returncode:
            bad.append((client, result.returncode, result.stderr[-200:]))
    except ValueError as error:
        bad.append((client, result.returncode, str(error)[:80]))
check("every client writes UTF-8 when stdout uses a legacy code page", not bad, bad)

print(f"\n{fails} failure(s)")
raise SystemExit(1 if fails else 0)
