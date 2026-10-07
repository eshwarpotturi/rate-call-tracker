"""Builds index.html (for GitHub Pages) from template.html, data.json and scores.json. Run score.py first."""
import json
t = open("template.html").read()
t = t.replace("/*DATA*/", json.dumps(json.load(open("data.json")))).replace("/*SCORES*/", json.dumps(json.load(open("scores.json"))))
head, body = t.split("</style>", 1)
open("index.html", "w").write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    + head + "</style>\n</head>\n<body>" + body + "\n</body>\n</html>\n")
print("built")
