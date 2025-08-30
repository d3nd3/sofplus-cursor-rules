.PHONY: format diff map map-check validate validate-examples fix-examples-spaces check

format:
	python3 tools/format_sofplus_docs.py --write

diff:
	python3 tools/format_sofplus_docs.py --diff

map:
	python3 tools/build_map.py --write

map-check:
	python3 tools/build_map.py | diff -u - .cursor/rules/sofplus-api/map.json

validate:
	python3 tools/validate_docs.py

validate-examples:
	python3 tools/validate_examples.py

check: diff map-check validate validate-examples

fix-examples-spaces:
	@find examples -type f -name '*.func' -print0 | xargs -0 -I{} bash -c 'expand -t 2 "{}" > "{}".tmp && mv "{}".tmp "{}"'


