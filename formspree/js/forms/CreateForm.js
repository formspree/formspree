/** @format */

const url = require('url')
const isValidUrl = require('valid-url').isWebUri
const isValidEmail = require('is-valid-email')
const React = require('react')
const toastr = window.toastr
const fetch = window.fetch

import Modal from '../Modal'

export default class CreateForm extends React.Component {
  constructor(props) {
    super(props)

    this.openModal = this.openModal.bind(this)
    this.closeModal = this.closeModal.bind(this)
    this.setEmail = this.setEmail.bind(this)
    this.setURL = this.setURL.bind(this)
    this.setSitewide = this.setSitewide.bind(this)
    this.validate = this.validate.bind(this)
    this.create = this.create.bind(this)
    this.checkSitewide = this.checkSitewide.bind(this)

    this.state = {
      modalOpened: false,

      url: '',
      email: '',
      sitewide: false,

      invalid: null,
      verified: false,
      disableVerification: false
    }
  }

  render() {
    let {
      email,
      url: urlv,
      sitewide,
      invalid,
      verified,
      disableVerification
    } = this.state

    return (
      <div className="col-1-1">
        <div className="create-form">
          <a href="#" onClick={this.openModal} className="button">
            Create a form
          </a>

          <Modal
            opened={this.state.modalOpened}
            onClose={this.closeModal}
            title="Create form"
          >
            <div className="container">
              <form onSubmit={this.create}>
                <div className="col-1-1">
                  <h4>Send email to:</h4>
                  <input
                    type="email"
                    onChange={this.setEmail}
                    value={email}
                    placeholder="You can point this form to any email address"
                  />
                </div>
                <div className="col-1-1">
                  <h4>From URL:</h4>
                  <input
                    type="url"
                    onChange={this.setURL}
                    value={urlv}
                    placeholder="Leave blank to send confirmation email when first submitted"
                  />
                </div>
                <div className="container">
                  <div className="col-1-4">
                    <label
                      className="hint--bottom"
                      data-hint="A site-wide form is a form that you can place on all pages of your website -- and you just have to confirm once!"
                    >
                      <input
                        type="checkbox"
                        checked={sitewide}
                        onChange={this.setSitewide}
                        value="true"
                      />
                      site-wide
                    </label>
                  </div>
                  <div className="col-3-4 info">
                    {invalid ? (
                      <div className="red">
                        {invalid === 'email' ? (
                          'Please input a valid email address.'
                        ) : (
                          <>
                            Please input a valid URL, for example:
                            <span className="code">
                              {url.resolve(
                                'http://www.mywebsite.com',
                                sitewide ? '' : '/contact.html'
                              )}
                            </span>
                          </>
                        )}
                      </div>
                    ) : !sitewide || (sitewide && verified) ? (
                      <div>&#8203;</div>
                    ) : (
                      <span>
                        Please ensure
                        <span className="code">
                          {url.resolve(urlv, '/formspree-verify.txt')}
                        </span>
                        exists and contains a line with
                        <span className="code">{email}</span>
                      </span>
                    )}
                  </div>
                </div>
                <div className="col-1-3">
                  <div className="verify">
                    <button
                      style={sitewide ? {} : {visibility: 'hidden'}}
                      disabled={!sitewide && !invalid && !disableVerification}
                      onClick={this.checkSitewide}
                    >
                      Verify
                    </button>
                  </div>
                </div>
                <div className="col-1-3">&#8203;</div>
                <div className="col-1-3">
                  <div className="create">
                    <button
                      type="submit"
                      disabled={
                        !((sitewide && verified) || (!sitewide && !invalid))
                      }
                    >
                      Create form
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </Modal>
        </div>
      </div>
    )
  }

  setEmail(e) {
    this.setState({email: e.target.value}, this.validate)
  }

  setURL(e) {
    this.setState({url: e.target.value}, this.validate)
  }

  setSitewide(e) {
    this.setState({sitewide: e.target.checked}, this.validate)
  }

  validate() {
    this.setState(st => {
      st.invalid = null

      let {email, url: urlv, sitewide} = st
      urlv = /^https?:\/\//.test(urlv) ? urlv : 'http://' + urlv

      if (!isValidEmail(email)) {
        st.invalid = 'email'
        return
      }

      if (sitewide) {
        if (urlv && !isValidUrl(urlv)) {
          st.invalid = 'urlv'
        }
      } else {
        if (urlv && urlv !== 'http://' && !isValidUrl(urlv)) {
          st.invalid = 'urlv'
        }
      }

      return st
    })
  }

  async checkSitewide(e) {
    e.preventDefault()

    try {
      let resp = await fetch(`/api-int/forms/sitewide-check`, {
        method: 'POST',
        body: JSON.stringify({email: this.state.email, url: this.state.url}),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        }
      })
      let r = await resp.json()

      if (!resp.ok || !r.ok) {
        toastr.warning("The verification file wasn't found.")
        this.setState({verified: false, disableVerification: true})

        setTimeout(() => {
          this.setState({disableVerification: false})
        }, 5000)
        return
      }

      toastr.success('The file exists! you can create your site-wide form now.')
      this.setState({verified: true})
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed to call the sitewide verification API, see the console for more details.'
      )
    }
  }

  async create(e) {
    e.preventDefault()

    try {
      let resp = await fetch('/api-int/forms', {
        method: 'POST',
        body: JSON.stringify({
          email: this.state.email,
          url: this.state.url,
          sitewide: this.state.sitewide
        }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        }
      })
      let r = await resp.json()

      if (!r.ok || r.error) {
        toastr.warning(
          r.error
            ? `Error creating form: ${r.error}`
            : 'Unexpected error creating form.'
        )
        return
      }

      toastr.success('Form created!')
      this.props.history.push(`/forms/${r.hashid}/integration`)
    } catch (e) {
      console.error(e)
      toastr.error('Failed to create form, see the console for more details.')
    }
  }

  openModal(e) {
    e.preventDefault()
    this.setState({modalOpened: true})
  }

  closeModal(e) {
    e.preventDefault()
    this.setState({modalOpened: false})
  }
}
