(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const $ = window.$
const StripeCheckout = window.StripeCheckout
const toastr = window.toastr

/* top navbar */
var nav = $('body > nav')
nav.addClass('js')
nav.find('.menu').slicknav()
nav.find('h4').clone().prependTo('.slicknav_menu')

/* adding a shadow at the bottom of the menu bar only when not at the top */
var w = $(window)
w.scroll(function () {
  var scrollPos = w.scrollTop()
  if (scrollPos && !nav.hasClass('scrolled')) {
    nav.addClass('scrolled')
  } else if (!scrollPos) {
    nav.removeClass('scrolled')
  }
})

/* background-color should inherit, but CSS's "inherit" breaks z-index */
var bgcolor = $(document.body).css('background-color')
if (bgcolor.split(',').length === 4 || bgcolor === 'transparent') {
  bgcolor = 'white'
}
nav.css('background-color', bgcolor)

/* modal */
$('.modal').each(function () {
  var modal = $(this)
  modal.addClass('js')
  var id = modal.attr('id')
  $('[href="#' + id + '"]').click(function (e) {
    e.preventDefault()
    modal.toggleClass('target')
  })
  modal.click(function (e) {
    if (e.target === modal[0]) {
      modal.toggleClass('target')
      e.preventDefault()
    }
  })
  modal.find('.x a').click(function (e) {
    e.preventDefault()
    modal.toggleClass('target')
  })
})

/* turning flask flash messages into js popup notifications */
toastr.options = { positionClass: 'toast-top-center' }
window.popupMessages.forEach(function (m, i) {
  var category = m[0] || 'info'
  var text = m[1]
  setTimeout(function () { toastr[category](text) }, (1 + i) * 1500)
})

/* stripe checkout */
var stripebutton = $('#stripe-upgrade')
if (stripebutton.length) {
  var handler = StripeCheckout.configure(stripebutton.data())
  stripebutton.on('click', function (e) {
    handler.open({
      token: function (token) {
        stripebutton.closest('form')
          .append(`<input type="hidden" name="stripeToken" value="${token.id}">`)
          .append(`<input type="hidden" name="stripeEmail" value="${token.email}">`)
          .submit()
      }
    })
    e.preventDefault()
  })
}

/* quick script for showing the resend confirmation form */
$('a.resend').on('click', function () {
  $(this).hide()
  $('form.resend').show()
})

},{}]},{},[1]);
