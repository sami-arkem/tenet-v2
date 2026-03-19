from src.core.pack_loader import (
    load_domain_packs,
    load_jurisdiction_packs,
    supported_domains_for_jurisdiction,
    control_ids_for_domain,
    composed_control_ids,
)

print("JURISDICTIONS")
for key, pack in load_jurisdiction_packs().items():
    print(key, pack["supported_domains"])

print("\nDOMAINS")
for key, pack in load_domain_packs().items():
    print(key, pack["control_ids"])

print("\nCOMPOSED AML+SANCTIONS+GOVERNANCE")
print(composed_control_ids(["aml", "sanctions", "governance"]))

print("\nUS SUPPORTED DOMAINS")
print(supported_domains_for_jurisdiction("US"))

print("\nSCREENING CONTROLS")
print(control_ids_for_domain("screening"))
