build: clean
	@echo
	@echo "> Building Python source distribution package..."
	python setup.py build
	@echo

sdist: clean
	@echo
	@echo "> Creating Python source distribution package..."
	python setup.py sdist

	@echo
	@echo "> Source distribution package successfully generated in ./dist/"
	@echo

upload: clean
	@echo
	@echo "> Uploading Python source distribution package..."
	python setup.py register sdist upload
	@echo

clean:
	@echo
	@echo "> Cleaning up..."
	rm -rf build dist varnishsentry-* *.egg-info
	find . -name "*.pyc" | xargs rm -f
	find . -name "__pycache__" -o -name ".DS_Store" | xargs rm -rf
