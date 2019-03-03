SHELL = /bin/sh

.PHONY: test clean setup devsetup dist

test:
	python3 -m pytest --cov=radguestauth
	coverage html -d cover
	bash ./integration_test.sh

devsetup: setup
	pip3 install -r dev-requirements.txt

setup:
	pip3 install -r requirements.txt

dist:
	python3 setup.py bdist_wheel
	# write latest version file for use in other scripts like image build
	grep '^Version: ' radguestauth.egg-info/PKG-INFO | sed 's/Version: //g' >dist/radguestauth-ver

clean:
	-find . -type d -name __pycache__ | xargs rm -r
	-find . -type f -name *.pyc | xargs rm
	rm -rf .coverage cover
	rm -rf build radguestauth.egg-info
