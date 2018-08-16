/** @format */

const $ = window.$

module.exports = function modals() {
  $('.modal').each(function() {
    let modal = $(this)
    modal.addClass('js')
    let id = modal.attr('id')

    $(`[href="#${id}"]`).click(function(e) {
      // open the modal
      e.preventDefault()
      modal.toggleClass('target')
    })

    modal.click(function(e) {
      // close the modal
      if (e.target === modal[0]) {
        cleanHash()
        modal.toggleClass('target')
        e.preventDefault()
      }
    })
    modal.find('.x a').click(function(e) {
      // close the modal
      cleanHash()
      e.preventDefault()
      modal.toggleClass('target')
    })
  })

  function cleanHash() {
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
