import re
import os
import shutil

from aqt.utils import tooltip, askUser
from aqt.qt import QFileDialog

from anki.hooks import addHook

IMG_TAG_RE = re.compile(r"<img[^>]+src=[\"']?([^\"'>]+)[\"']?[^>]*>", re.IGNORECASE)
COLLECTION_PATH = "home/adel/.local/share/Anki2/BL/collection.media"
DEBUG = False

def most_important_tag(full_tags):
    """Returns most important tag from tag list"""
    # TODO: Rank tags based on prefixes from popular decks
    # important_tag_prefixes = [
    #     "Zanki",
    #     "#"
    #     "Dorian"
    #     "AQ"
    # ]
    # unimportant_tag_prefixes = [
    #     "$",
    #     "^"
    # ]
    return max(full_tags, key=len)

def convert_filename(filename, tag):
    """Creates a new filename that incorporates the deck tags

    Double underscore added between tag part of filename and old filename"""
    # TODO: Replace any characters that are valid tags but not filenames
    # TODO: Make separator configurable
    # TODO: Check for starting string to avoid doing it twice
    tag_list = tag.split("::")
    tag_part = "_".join(tag_list) + "__"
    tag_name_part = tag_part.lower()
    return tag_name_part + filename

def rename_images(note):
    """Returns whether note was changed"""
    # TODO: Add GUI/configuration to select field or at least do all fields
    image_val = note["Image"]
    image_tags = re.findall(IMG_TAG_RE, image_val)
    if len(image_tags) == 0:
        return 0

    tag_for_rename = most_important_tag(note.tags)
    for old_filename in image_tags:
        new_filename = convert_filename(old_filename, tag_for_rename)
        image_val = image_val.replace(old_filename, new_filename)
        old_path = os.path.join(COLLECTION_PATH, old_filename)
        new_path = os.path.join(COLLECTION_PATH, new_filename)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            shutil.move(old_path, new_path)
        else:
            assert os.path.exists(new_path), new_path
    note["Image"] = image_val
    # TODO: Need to change this if renaming becomes more selective
    return len(image_tags)

def on_rename_images(browser):
    if not askUser("Have you backed up your collection and media folder?"):
        tooltip("Image renaming cancelled")
        return
    mw = browser.mw
    global COLLECTION_PATH
    COLLECTION_PATH = mw.col.media.dir()
    nids = browser.selectedNotes()
    affected_images = 0
    affected_notes = 0
    if not nids:
        tooltip("No cards selected.")
        return
    # rename_images(nids)
    mw.progress.start(max=len(nids), min=0, immediate=True)
    for nid in nids:
        note = mw.col.getNote(nid)
        changed = rename_images(note)
        if changed:
            affected_images += changed
            affected_notes += 1
            note.flush()
        mw.progress.update()
    mw.progress.finish()
    browser.mw.reset()
    tooltip("Renamed {} images in {} notes".format(affected_images, affected_notes))

def on_save_selected_imgs(browser):
    mw = browser.mw
    nids = browser.selectedNotes()
    imgs = set()
    if not nids:
        tooltip("No cards selected.")
        return
    mw.progress.start(max=len(nids), min=0, immediate=True)
    for nid in nids:
        note = mw.col.getNote(nid)
        filename = re.findall(IMG_TAG_RE, note["Image"])[0]
        imgs.add(filename)
        mw.progress.update()
    mw.progress.finish()
    savefilename = QFileDialog.getSaveFileName(
        caption="Save image filenames",
        directory="image_filenames.txt"
    )
    with open(savefilename[0], "w") as f:
        for imgname in imgs:
            f.write("%s\n" % imgname)
    tooltip("Saved {} images from {} notes".format(len(imgs), len(nids)))

def setup_menu(browser):
    menu = browser.form.menuEdit
    # Renaming
    raction = menu.addAction("Rename images")
    raction.triggered.connect(lambda _, b = browser: on_rename_images(b))
    # Save image filenames to a file
    saction = menu.addAction("Save image filenames")
    saction.triggered.connect(lambda _, b = browser: on_save_selected_imgs(b))

if __name__ != "__main__":
    addHook("browser.setupMenus", setup_menu)

if __name__ == "__main__":
    import unittest

    class TestReformatFilename(unittest.TestCase):
        def test_most_important_tag(self):
            assert most_important_tag(["BlueLink::Face"]) == "BlueLink::Face"

        def test_convert_filename(self):
            assert convert_filename("tmp_bmmshsc.png", "BlueLink::Face") == "bluelink_face__tmp_bmmshsc.png"

    unittest.main()
