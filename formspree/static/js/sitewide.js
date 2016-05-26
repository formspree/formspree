const url = require('url')
const isValidUrl = require('valid-url').isWebUri
const isValidEmail = require('is-valid-email')

const h = require('virtual-dom/h')
const diff = require('virtual-dom/diff')
const patch = require('virtual-dom/patch')
const createElement = require('virtual-dom/create-element')

const $ = window.$
const toastr = window.toastr

/* create-form validation for site-wide forms */
module.exports = function sitewide () {
  var parentNode = $('#create-form .container')
  if (!parentNode.length) return

  let formActionURL = parentNode.find('form').attr('action')
  let currentUserEmail = parentNode.find('[name="email"]').val()
  let emailPlaceholder = parentNode.find('[name="email"]').attr('placeholder')
  let urlPlaceholder = parentNode.find('[name="url"]').attr('placeholder')
  let sitewideHint = parentNode.find('label[data-hint]').data('hint')

  // since we have javascript, let's trash this HTML and recreate with virtual-dom

  var data = {
    invalid: null,
    sitewide: false,
    verified: false,
    email: currentUserEmail
  }
  var tree = render(data)
  var rootNode = createElement(tree)
  parentNode[0].replaceChild(rootNode, parentNode.find('form')[0])

  parentNode.on('change', 'input[name="sitewide"]', run)
  parentNode.on('input', 'input[name="url"], input[name="email"]', run)
  parentNode.on('click', '.verify button', check)

  function run () {
    let checkbox = parentNode.find('input[name="sitewide"]')

    let email = parentNode.find('input[name="email"]').val().trim()
    let urlv = parentNode.find('input[name="url"]').val().trim()
    urlv = /^https?:\/\//.test(urlv) ? urlv : 'http://' + urlv
    let sitewide = checkbox.is(':checked')

    // wrong input
    if (!isValidEmail(email)) { // invalid email
      data.invalid = 'email'
    } else if (sitewide && !isValidUrl(urlv)) { // invalid url with sitewide
      data.invalid = 'url'
    } else if (!sitewide && urlv && urlv !== 'http://' && !isValidUrl(urlv)) { // invalid url without sitewide
      data.invalid = 'url'
    } else {
      data.invalid = null
    }

    data.sitewide = sitewide
    data.urlv = urlv
    data.email = email

    apply(render(data))
  }

  function check () {
    $.ajax({
      url: '/forms/sitewide-check?' + parentNode.find('form').serialize(),
      success: function () {
        toastr.success('The file exists! you can create your site-wide form now.')
        data.verified = true
        apply(render(data))
      },
      error: function () {
        toastr.warning("The verification file wasn't found.")
        data.verified = false
        data.disableVerification = true
        apply(render(data))

        setTimeout(() => {
          data.disableVerification = false
          apply(render(data))
        }, 5000)
      }
    })

    return false
  }

  function apply (vtree) {
    let patches = diff(tree, vtree)
    rootNode = patch(rootNode, patches)
    tree = vtree
  }

  function render ({invalid, sitewide, verified, urlv, email, disableVerification}) {
    return h('form', {method: 'post', action: formActionURL}, [
      h('.col-1-1', [
        h('h4', 'Send email to:'),
        h('input', {type: 'email', name: 'email', placeholder: emailPlaceholder, value: email})
      ]),
      h('.col-1-1', [
        h('h4', 'From URL:'),
        h('input', {type: 'text', name: 'url', placeholder: urlPlaceholder})
      ]),
      h('.container', [
        h('.col-1-4', [
          h('label.hint--bottom', {dataset: {hint: sitewideHint}}, [
            h('input', {type: 'checkbox', name: 'sitewide', value: 'true'}),
            ' site-wide'
          ])
        ]),
        h('.col-3-4.info', [
          invalid
            ? h('div.red', invalid === 'email'
              ? 'Please input a valid email address.'
              : [
                'Please input a valid URL. For example: ',
                h('span.code', url.resolve('http://www.mywebsite.com', sitewide ? '' : '/contact.html'))
              ])
            : sitewide && verified || !sitewide
              ? h('div', {innerHTML: '&#8203;'})
              : h('span', [
                'Please ensure ',
                h('span.code', url.resolve(urlv, '/formspree-verify.txt')),
                ' exists and contains a line with ',
                h('span.code', email)
              ])
        ]),
        h('.col-1-3', [
          h('.verify', [
            h('button', sitewide && !invalid && !disableVerification
              ? {}
              : sitewide
                ? {disabled: true}
                : {style: {visibility: 'hidden'}, disabled: true},
            'Verify')
          ])
        ]),
        h('.col-1-3', {innerHTML: '&#8203;'}),
        h('.col-1-3', [
          h('.create', [
            sitewide && verified || !sitewide && !invalid
              ? h('button', {type: 'submit'}, 'Create form')
              : h('button', {disabled: true}, 'Create form')
          ])
        ])
      ])
    ])
  }
}
