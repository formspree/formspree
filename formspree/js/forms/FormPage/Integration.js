/** @format */

const React = require('react')
const CodeMirror = require('react-codemirror2')
const cs = require('class-set')
require('codemirror/mode/xml/xml')
require('codemirror/mode/javascript/javascript')

const {Link} = require('react-router-dom')

module.exports = class FormIntegration extends React.Component {
  constructor(props) {
    super(props)

    this.changeTab = this.changeTab.bind(this)

    this.state = {
      activeTab: 'HTML',
      availableTabs: ['HTML', 'AJAX']
    }
  }

  render() {
    let {form} = this.props

    var codeSample
    var modeSample
    switch (this.state.activeTab) {
      case 'HTML':
        modeSample = 'xml'
        codeSample = `<form
  action="${form.url}"
  method="POST"
>
  <label>
    Your email:
    <input type="text" name="_replyto">
  </label>
  <label>
    Your message:
    <textarea name="message"></textarea>
  </label>

  <!-- your other form fields go here -->

  <button type="submit">Send</button>
</form>`
        break
      case 'AJAX':
        modeSample = 'javascript'
        codeSample = `// There should be an HTML form elsewhere on the page. See the "HTML" tab.
var form = document.querySelector('form')
var data = new FormData(form)
var req = new XMLHttpRequest()
req.open(form.method, form.action)
req.send(data)`
        break
    }

    var integrationSnippet
    if (this.state.activeTab === 'AJAX' && !form.captcha_disabled) {
      integrationSnippet = (
        <div className="integration-nocode CodeMirror cm-s-oceanic-next">
          <p>Want to submit your form through AJAX?</p>
          <p>
            <Link to={`/forms/${form.hashid}/settings`}>Disable reCAPTCHA</Link>{' '}
            for this form to make it possible!
          </p>
        </div>
      )
    } else {
      integrationSnippet = (
        <CodeMirror.UnControlled
          value={codeSample}
          options={{
            theme: 'oceanic-next',
            mode: modeSample,
            viewportMargin: Infinity
          }}
        />
      )
    }

    return (
      <>
        <div className="col-1-1">
          <div className="container">
            <div className="integration">
              <p>
                Paste this code in your HTML, modifying it according to your
                needs:
              </p>
              <div className="integration-tabs">
                {this.state.availableTabs.map(tabName => (
                  <div
                    key={tabName}
                    data-tab={tabName}
                    onClick={this.changeTab}
                    className={cs({active: this.state.activeTab === tabName})}
                  >
                    {tabName}
                  </div>
                ))}
              </div>
              {integrationSnippet}
            </div>
          </div>
        </div>
      </>
    )
  }

  changeTab(e) {
    e.preventDefault()

    this.setState({activeTab: e.target.dataset.tab})
  }
}
