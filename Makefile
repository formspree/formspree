all: formspree/static/bundle.js formspree/static/main.css

watch:
	find formspree/js/ formspree/scss/ -name '*.js' -o -name '*.scss' | entr make

$(shell find formspree/js/):
	./node_modules/.bin/prettier "formspree/js/**/*.js"

formspree/static/bundle.js: $(shell find formspree/js)
	./node_modules/.bin/browserify formspree/js/main.js -dv --outfile formspree/static/bundle.js

formspree/static/bundle.min.js:  $(shell find formspree/js)
	./node_modules/.bin/browserify formspree/js/main.js -g [ envify --NODE_ENV production ] -g uglifyify | ./node_modules/.bin/uglifyjs --compress --mangle > formspree/static/bundle.min.js

formspree/static/main.css:  $(shell find formspree/scss) dart-sass/src/dart
	cd dart-sass && ./sass ../formspree/scss/main.scss ../formspree/static/main.css

dart-sass/src/dart:
	echo -e "\n\ninstall dart-sass from https://github.com/sass/dart-sass/releases\n\n"
