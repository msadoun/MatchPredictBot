from types import SimpleNamespace

from user_broadcast import (
    copy_caption_for_command,
    image_source_message,
    is_image_message,
    split_bot_command,
)


def test_split_bot_command_from_caption():
    assert split_bot_command("/broadcast@FTM3naBot confirm مرحبا") == (
        "broadcast",
        ["confirm", "مرحبا"],
    )
    assert split_bot_command("/senduser @msadoun صورة") == (
        "senduser",
        ["@msadoun", "صورة"],
    )
    assert split_bot_command("not a command") is None
    assert split_bot_command(None) is None


def test_is_image_message_photo_and_image_document():
    photo = SimpleNamespace(photo=[object()], document=None)
    image_doc = SimpleNamespace(
        photo=None,
        document=SimpleNamespace(mime_type="image/jpeg"),
    )
    pdf = SimpleNamespace(
        photo=None,
        document=SimpleNamespace(mime_type="application/pdf"),
    )
    assert is_image_message(photo)
    assert is_image_message(image_doc)
    assert not is_image_message(pdf)
    assert not is_image_message(None)


def test_image_source_prefers_current_then_reply():
    photo = SimpleNamespace(photo=[object()], document=None, reply_to_message=None)
    text = SimpleNamespace(photo=None, document=None, reply_to_message=photo)
    assert image_source_message(photo) is photo
    assert image_source_message(text) is photo


def test_copy_caption_for_command():
    assert copy_caption_for_command("عنوان", image_is_command_message=True) == "عنوان"
    assert copy_caption_for_command("", image_is_command_message=True) == ""
    assert copy_caption_for_command("", image_is_command_message=False) is None
