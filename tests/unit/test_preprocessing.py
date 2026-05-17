from src.service.preprocessing.text import normalize, tokenize, extract_attributes


def test_normalize_shcs():
    out = normalize('SHCS M8 x 30mm')
    assert 'socket' in out
    assert 'head' in out
    assert 'cap' in out
    assert 'screw' in out
    assert 'm8' in out


def test_normalize_hhb():
    out = normalize('HHB 3/4-10 x 5/8')
    assert 'hex' in out
    assert '3/4-10' in out


def test_normalize_finish_abbrevs():
    out = normalize('HDG YZ BO PLN')
    assert 'hot dip galvanized' in out
    assert 'yellow zinc' in out
    assert 'black oxide' in out
    assert 'plain' in out


def test_normalize_catalog_abbrevs():
    out = normalize('HX CAP SCR 18-8 SS MECH ZN')
    assert 'hex' in out
    assert 'stainless steel' in out
    assert 'mechanical zinc' in out


def test_normalize_preserves_thread():
    out = normalize('M8-1.25 X 30MM SOCKET HEAD CAP SCR STEEL BLACK OXIDE')
    assert 'm8-1.25' in out
    assert 'socket' in out


def test_extract_metric_thread():
    attrs = extract_attributes('M8-1.25 X 30MM SOCKET HEAD CAP SCR STEEL BLACK OXIDE')
    assert attrs['thread'] == 'm8-1.25'
    assert attrs['length'] == '30mm'
    assert attrs['type'] == 'socket head cap screw'
    assert attrs['material'] == 'steel'
    assert attrs['finish'] == 'black oxide'


def test_extract_imperial_thread():
    attrs = extract_attributes('3/8-16 X 1-1/2 HX CAP SCREW 316 SS YELLOW ZN')
    assert attrs['thread'] == '3/8-16'
    assert attrs['type'] == 'hex cap screw'
    assert attrs['finish'] == 'yellow zinc'


def test_extract_numbered_thread():
    attrs = extract_attributes('#10-24 FLAT WASHER 18-8 SS ZINC')
    assert attrs['thread'] == '#10-24'
    assert attrs['type'] == 'flat washer'


def test_extract_hdg_finish():
    attrs = extract_attributes('M12-1.75 HEX NUT CLASS 8 STEEL HDG')
    assert attrs['type'] == 'hex nut'
    assert attrs['finish'] == 'hot dip galvanized'


def test_tokenize_drops_stopwords():
    tokens = tokenize('a hex cap screw in the catalog')
    assert 'a' not in tokens
    assert 'the' not in tokens
    assert 'in' not in tokens
    assert 'hex' in tokens
