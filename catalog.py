POOL_BY_BRAND = {
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

SEGMENTS = ("ADULTS", "KIDS")

def pool_for(brand, segment):
    return POOL_BY_BRAND.get((brand, segment))


def pairs_in_pool(pool):
    result = []
    for pair, label in POOL_BY_BRAND.items():
        if label == pool:
            result.append(pair)
    return result


def pool_labels():
    return sorted(set(POOL_BY_BRAND.values()))

def brands_for_segment(segment):
    result = []
    for brand, rule_segment in POOL_BY_BRAND:
        if rule_segment == segment:
            result.append(brand)
    return sorted(result)        

