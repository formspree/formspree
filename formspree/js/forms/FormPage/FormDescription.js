/** @format */

const React = require('react') // eslint-disable-line no-unused-vars

export default function FormDescription({prefix, form}) {
  return (
    <h2 className="form-description">
      {prefix}{' '}
      {!form.hash ? (
        <span className="code">/{form.hashid}</span>
      ) : (
        <span className="code">/{form.email}</span>
      )}
    </h2>
  )
}
