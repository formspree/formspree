const url = require('url')
const isValidEmail = require('is-valid-email')

const $ = window.$
const StripeCheckout = window.StripeCheckout
const toastr = window.toastr

toastr.options = { positionClass: 'toast-top-center' }

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

/* create-form validation for site-wide forms */
function sitewide () {
  let createform = $('#create-form')
  let emailInput = createform.find('input[name="email"]')
  let urlInput = createform.find('input[name="url"]')
  let checkbox = createform.find('input[name="sitewide"]')
  let verifyButton = createform.find('.verify-button')
  let createButton = createform.find('.create-button')
  let info = createform.find('.verify-info')

  checkbox.on('change', run)
  emailInput.on('input', run)
  urlInput.on('input', run)

  function run () {
    if (checkbox.is(':checked')) {
      let email = emailInput.val().trim()
      let urlp = url.parse(urlInput.val().trim())

      if (isValidEmail(email) && urlp.host) {
        let sitewideFile = `formspree_verify_${email}.txt`
        verifyButton.css('visibility', 'visible')
        info.html(`Please ensure <span class="code">${url.resolve(urlInput.val(), '/' + sitewideFile)}</span> exists`)
      } else {
        // wrong input
        if (!urlp.host) { // invalid url
          info.text('Please input a valid URL.')
        } else { // invalid email
          info.text('Please input a valid email address.')
        }
      }

      createButton.find('button').prop('disabled', true)
      info.css('visibility', 'visible')
    } else {
      // toggle sitewide off
      info.css('visibility', 'hidden')
      verifyButton.css('visibility', 'hidden')
      createButton.css('visibility', 'visible')
    }
  }

  verifyButton.find('button').on('click', function () {
    $.ajax({
      url: '/forms/sitewide-check?' + createform.find('form').serialize(),
      success: function () {
        toastr.success('The file exists! you can create your site-wide form now.')
        createButton.find('button').prop('disabled', false)
        verifyButton.css('visibility', 'hidden')
        info.css('visibility', 'hidden')
      },
      error: function () {
        toastr.warning("The verification file wasn't found.")
        verifyButton.find('button').prop('disabled', true)
        setTimeout(() => {
          verifyButton.find('button').prop('disabled', false)
        }, 5000)
      }
    })
    return false
  })
}
sitewide()

/* turning flask flash messages into js popup notifications */
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
