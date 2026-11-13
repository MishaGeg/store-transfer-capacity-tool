# Each (brand, age group) pair belongs to one shared capacity group.
BRAND_AGE_GROUP = {
    ("ECCO", "ADULTS"): "ECCOGEOXSTUDIO",
    ("GEOX", "ADULTS"): "ECCOGEOXSTUDIO",
    ("STUDIO", "ADULTS"): "ECCOGEOXSTUDIO",
    ("BATA", "ADULTS"): "BATABAMBINO",
    ("BAMB", "KIDS"): "BATABAMBINO",
    ("ECCO", "KIDS"): "BATABAMBINO",
    ("GEOX", "KIDS"): "BATABAMBINO",
    ("SCARPIERA", "ADULTS"): "SCARPIERA",
    ("REPLAY", "ADULTS"): "ECCOGEOXSTUDIO",
}

AGE_GROUPS = ("ADULTS", "KIDS")

def get_brand_group(brand, age_group):
    """Return the capacity group for an exact catalog pair, or None if unknown."""
    return BRAND_AGE_GROUP.get((brand, age_group))

def get_brand_age_group_pairs(brand_group):
    """Return all (brand, age group) pairs sharing this group's capacity."""
    result = []
    for brand_age_pair, group_name in BRAND_AGE_GROUP.items():
        if group_name == brand_group:
            result.append(brand_age_pair)
    return result

def get_brand_group_names():
    return sorted(set(BRAND_AGE_GROUP.values()))

def get_brands_by_age_group(age_group):
    result = []
    for brand, rule_age_group in BRAND_AGE_GROUP:
        if rule_age_group == age_group:
            result.append(brand)
    return sorted(result)        

