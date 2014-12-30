$(function () {
  $('.b64-input').on('input', function () { updateWith($(this)) })

  function updateWith ($input) {
    var decoded = ($input.val().trim() || 'you@example.com')
    var encodedURL = $input.data('baseaddr') + btoa(decoded)
    $('.b64-mirror').text(decoded)
    $('.b64-output-url').text(encodedURL)
  }

  updateWith($('.b64-input'))
})
