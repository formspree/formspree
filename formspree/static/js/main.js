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

/* modals -- working with or without JS */
function modals () {
  $('.modal').each(function () {
    let modal = $(this)
    modal.addClass('js')
    let id = modal.attr('id')

    $(`[href="#${id}"]`).click(function (e) {
      // open the modal
      e.preventDefault()
      modal.toggleClass('target')
    })

    modal.click(function (e) {
      // close the modal
      if (e.target === modal[0]) {
        cleanHash()
        modal.toggleClass('target')
        e.preventDefault()
      }
    })
    modal.find('.x a').click(function (e) {
      // close the modal
      cleanHash()
      e.preventDefault()
      modal.toggleClass('target')
    })
  })

  function cleanHash () {
    if (!window.location.hash) return
    if (window.history && window.history.replaceState) {
      window.history.replaceState('', document.title, window.location.pathname)
    } else {
      let pos = $(window).scrollTop()
      window.location.hash = ''
      $(window).scrollTop(pos)
    }
  }

  // activate modals from url hash #
  setTimeout(() => {
    // setTimeout is needed because :target elements only appear after
    // the page is loaded or something like that.
    let activatedModal = $('*:target')
    if (activatedModal.length && !activatedModal.is('.target')) {
      activatedModal.toggleClass('target')
    }
  }, 0)
}
modals()

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
  return false
})

/* scripts at other files */
require('./sitewide')()

/* toggle the card management menu */
        $(function () {
            $("#card-list tr:even").addClass("even");
            $("#card-list tr:not(.even)").hide();
            $("#card-list tr:first-child").show();

            $("#card-list tr.even").click(function () {
                $(this).next("tr").toggle();
                $(this).find(".arrow").toggleClass("up");
                $(this).find(".fa-chevron-right").toggleClass("fa-rotate-90");
            });
        });
