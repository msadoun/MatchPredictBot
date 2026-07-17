from knockout_doubles import doubles_allowed_for_stage


def test_doubles_half_for_multi_match_stages():
    assert doubles_allowed_for_stage("دور الـ32") == 8
    assert doubles_allowed_for_stage("دور الـ16") == 4
    assert doubles_allowed_for_stage("ربع النهائي") == 2
    assert doubles_allowed_for_stage("نصف النهائي") == 1


def test_doubles_allowed_for_final_and_third_place():
    assert doubles_allowed_for_stage("مباراة المركز الثالث") == 1
    assert doubles_allowed_for_stage("النهائي") == 1


def test_doubles_zero_for_non_knockout():
    assert doubles_allowed_for_stage("المجموعة أ") == 0
    assert doubles_allowed_for_stage("") == 0
