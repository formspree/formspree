/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')

const FormDescription = require('./FormDescription')

module.exports = class FormSubmissions extends React.Component {
  constructor(props) {
    super(props)

    this.deleteSubmission = this.deleteSubmission.bind(this)
    this.showExportButtons = this.showExportButtons.bind(this)

    this.state = {
      exporting: false
    }
  }

  render() {
    let {form} = this.props

    return (
      <div className="col-1-1 submissions-col">
        <FormDescription prefix="Submissions for" form={form} />
        {form.submissions.length ? (
          <>
            <table className="submissions responsive">
              <thead>
                <tr>
                  <th>Submitted at</th>
                  {form.fields
                    .slice(1 /* the first field is 'date' */)
                    .map(f => (
                      <th key={f}>{f}</th>
                    ))}
                  <th />
                </tr>
              </thead>
              <tbody>
                {form.submissions.map(s => (
                  <tr id={`submission-${s.id}`} key={s.id}>
                    <td id={`p-${s.id}`} data-label="Submitted at">
                      {new Date(Date.parse(s.date))
                        .toString()
                        .split(' ')
                        .slice(0, 5)
                        .join(' ')}
                    </td>
                    {form.fields
                      .slice(1 /* the first field is 'date' */)
                      .map(f => (
                        <td data-label={f} key={f}>
                          <pre>{s[f]}</pre>
                        </td>
                      ))}
                    <td>
                      <button
                        className="no-border"
                        data-sub={s.id}
                        onClick={this.deleteSubmission}
                      >
                        <i className="fa fa-trash-o delete" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="container">
              <div className="row">
                {this.state.exporting ? (
                  <div className="col-1-1 right">
                    <a
                      target="_blank"
                      className="button"
                      style={{marginRight: '5px'}}
                      href={`/forms/${form.hashid}.json`}
                    >
                      Export as JSON
                    </a>
                    <a
                      target="_blank"
                      className="button"
                      href={`/forms/${form.hashid}.csv`}
                    >
                      Export as CSV
                    </a>
                  </div>
                ) : (
                  <div className="col-1-1 right">
                    <button
                      onClick={this.showExportButtons}
                      href={`/forms/${form.hashid}.json`}
                    >
                      Export
                    </button>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <h3>No submissions archived yet.</h3>
        )}
      </div>
    )
  }

  showExportButtons(e) {
    e.preventDefault()
    this.setState({exporting: true})
  }

  async deleteSubmission(e) {
    e.preventDefault()

    let subid = e.currentTarget.dataset.sub

    try {
      let resp = await fetch(
        `/api-int/forms/${this.props.form.hashid}/submissions/${subid}`,
        {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: {Accept: 'application/json'}
        }
      )
      let r = await resp.json()

      if (!resp.ok || r.error) {
        toastr.warning(
          r.error
            ? `Failed to delete submission: ${r.error}`
            : `Failed to delete submission.`
        )
        return
      }

      toastr.success('Submission deleted.')
      this.props.onUpdate()
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed to delete submission, see the console for more details.'
      )
    }
  }
}
