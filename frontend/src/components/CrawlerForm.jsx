import { useState, useEffect } from 'react'
import './CrawlerForm.css'

function CrawlerForm({ validators, onStartCrawl, isRunning }) {
  const [url, setUrl] = useState('')
  const [selectedValidators, setSelectedValidators] = useState([])

  // Select all validators by default
  useEffect(() => {
    if (validators.length > 0) {
      setSelectedValidators(validators.map(v => v.id))
    }
  }, [validators])

  const handleValidatorToggle = (validatorId) => {
    setSelectedValidators(prev => {
      if (prev.includes(validatorId)) {
        return prev.filter(id => id !== validatorId)
      } else {
        return [...prev, validatorId]
      }
    })
  }

  const handleSelectAll = () => {
    setSelectedValidators(validators.map(v => v.id))
  }

  const handleDeselectAll = () => {
    setSelectedValidators([])
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (url && selectedValidators.length > 0) {
      onStartCrawl(url, selectedValidators)
    }
  }

  return (
    <div className="crawler-form-container">
      <h2>Configure Crawl</h2>
      <form onSubmit={handleSubmit} className="crawler-form">
        <div className="form-group">
          <label htmlFor="url">Website URL</label>
          <input
            type="url"
            id="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            required
            disabled={isRunning}
            className="url-input"
          />
        </div>

        <div className="form-group">
          <div className="validators-header">
            <label>Validators</label>
            <div className="validator-actions">
              <button 
                type="button" 
                onClick={handleSelectAll}
                disabled={isRunning}
                className="action-btn"
              >
                Select All
              </button>
              <button 
                type="button" 
                onClick={handleDeselectAll}
                disabled={isRunning}
                className="action-btn"
              >
                Deselect All
              </button>
            </div>
          </div>

          <div className="validators-list">
            {validators.map((validator) => (
              <div key={validator.id} className="validator-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedValidators.includes(validator.id)}
                    onChange={() => handleValidatorToggle(validator.id)}
                    disabled={isRunning}
                  />
                  <div className="validator-info">
                    <span className="validator-name">{validator.name}</span>
                    <span className="validator-description">{validator.description}</span>
                  </div>
                </label>
              </div>
            ))}
          </div>
        </div>

        <button 
          type="submit" 
          className="scan-button"
          disabled={isRunning || !url || selectedValidators.length === 0}
        >
          {isRunning ? 'Scanning...' : 'Start Scan'}
        </button>
      </form>
    </div>
  )
}

export default CrawlerForm
