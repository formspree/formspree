/** @format */

const React = require('react') // eslint-disable-line no-unused-vars

export default function SettingsSwitch({
  title,
  fieldName,
  description,
  checkedFn,
  onChangeFn
}) {
  return (
    <>
      <div className="row">
        <div className="col-1-1">
          <h4>{title}</h4>
        </div>
        <div className="switch-row">
          <label className="switch">
            <input
              type="checkbox"
              onChange={onChangeFn()}
              checked={checkedFn()}
              name={fieldName}
            />
            <span className="slider" />
          </label>
        </div>
      </div>
      <div className="row">
        <div className="col-1-1">
          <p className="description">{description}</p>
        </div>
      </div>
    </>
  )
}
