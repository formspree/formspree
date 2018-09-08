all: formspree/static/bundle.js formspree/static/main.css

prod: formspree/static/bundle.min.js formspree/static/main.min.css

watch:
	find formspree/js/ formspree/scss/ -name '*.js' -o -name '*.scss' | entr make

format:
	./node_modules/.bin/prettier --write "formspree/js/**.js"
	./node_modules/.bin/prettier --write "formspree/scss/**.scss"

formspree/static/bundle.js: $(shell find formspree/js)
	./node_modules/.bin/browserify formspree/js/main.js -dv --outfile formspree/static/bundle.js

formspree/static/bundle.min.js:  $(shell find formspree/js)
	./node_modules/.bin/browserify formspree/js/main.js -g [ envify --NODE_ENV production ] -g uglifyify | ./node_modules/.bin/uglifyjs --compress --mangle > formspree/static/bundle.min.js

formspree/static/main.css:  $(shell find formspree/scss) dart-sass/src/dart
	cd dart-sass && ./sass ../formspree/scss/main.scss ../formspree/static/main.css

formspree/static/main.min.css:  $(shell find formspree/scss) dart-sass/src/dart
	cd dart-sass && ./sass --style=compressed ../formspree/scss/main.scss ../formspree/static/main.min.css

dart-sass/src/dart:
	FILE=`python3 -c 'print("dart-sass-1.13.0-" + ("linux" if "linux" in "'$$(uname -o)'".lower() else "macos") + "-" + ("x64" if "64" in "'$$(uname -m)'" else "ia32") + ".tar.gz")'` && \
        wget "https://github.com/sass/dart-sass/releases/download/1.13.0/$$FILE" -O $$FILE && \
        tar -xvf $$FILE && \
        rm $$FILE
