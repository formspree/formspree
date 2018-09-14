/** @format */

const React = require('react') // eslint-disable-line no-unused-vars

module.exports = FormDescription

function FormDescription({prefix, form}) {
  return (
    <h2 className="form-description">
      {prefix}{' '}
      {!form.hash ? (
        <span className="code">/{form.hashid}</span>
      ) : (
        <span className="code">/{form.email}</span>
      )}{' '}
      {form.host ? (
        <>
          at <span className="code">{form.host}</span>
          {form.sitewide ? ' and all its subpaths.' : null}
        </>
      ) : (
        ''
      )}
      {form.hash ? (
        <>
          <br />
          <small>
            you can now replace the email in the URL with{' '}
            <span className="code">{`/${form.hashid}`}</span>
          </small>
        </>
      ) : (
        <>
          <br />
          <small>
            targeting <span className="code">{form.email}</span>
          </small>
        </>
      )}
    </h2>
  )
}
