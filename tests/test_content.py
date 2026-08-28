from website.content import fmt_bytes, fmt_int


def test_integer_formatting():
    assert fmt_int(20682487) == "20,682,487"


def test_byte_size_formatting():
    cases = {
        327: "327 B",
        483: "483 B",
        1024: "1 KiB",
        524288: "0.50 MiB",
        379956346: "362.4 MiB",
        2445000000: "2.28 GiB",
        1024 * 1024 * 1024 + 1024 * 1024: "1.00 GiB",
    }
    for size, label in cases.items():
        assert fmt_bytes(size) == label
