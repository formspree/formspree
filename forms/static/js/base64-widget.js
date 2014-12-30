$(function () {
  $('.b64-input').on('input', function () {
    updateWith($(this), true)
  })

  function updateWith ($input, force) {
    var decoded = ($input.val().trim() || $input.text().trim() || 'you@email.com')
    var encodedURL = $input.data('baseaddr') + btoa(decoded)
    $('.b64-mirror').text(decoded)
    $('.b64-output-url').each(function () {
      $output = $(this)
      var preexisting = $output.val().trim() || $output.text().trim()
      if (preexisting && !force) {
        return
      }
      $output.text(encodedURL).val(encodedURL)
    })
  }

  updateWith($('.b64-input'))
})
