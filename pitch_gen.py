with open("assets/arch_b64.txt", "r") as f:
    arch_img = f.read().strip()

html = open("pitch_deck_template.html", "r", encoding="utf-8").read()
html = html.replace("ARCH_IMAGE_BASE64", arch_img)
with open("pitch_deck.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Done - pitch_deck.html created")
