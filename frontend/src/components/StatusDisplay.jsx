import { useState } from 'react'
import './StatusDisplay.css'

function StatusDisplay({ updates, isRunning }) {
  const [expandedValidators, setExpandedValidators] = useState(new Set())

  const toggleValidator = (validatorName) => {
    setExpandedValidators(prev => {
      const newSet = new Set(prev)
      if (newSet.has(validatorName)) {
        newSet.delete(validatorName)
      } else {
        newSet.add(validatorName)
      }
      return newSet
    })
  }

  // Get the crawling status
  const crawlingUpdate = updates.find(u => u.type === 'crawling' || u.stage === 'crawling')
  const crawlingStatus = crawlingUpdate?.status || 'running'

  // Get validator updates
  const validatorUpdates = updates.filter(u => u.type === 'validator')
  
  // Group validator updates by stage name (keep only the latest)
  const validatorMap = {}
  validatorUpdates.forEach(update => {
    validatorMap[update.stage] = update
  })

  // Get completion update
  const completionUpdate = updates.find(u => u.type === 'complete')
  
  // Get error update
  const errorUpdate = updates.find(u => u.type === 'error')

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <span className="spinner"></span>
      case 'success':
        return <span className="icon-success">✓</span>
      case 'failed':
        return <span className="icon-failed">✗</span>
      default:
        return null
    }
  }

  return (
    <div className="status-display">
      <h2>Scan Progress</h2>
      
      <div className="status-list">
        {/* Crawling Status */}
        <div className={`status-item crawling ${crawlingStatus}`}>
          <div className="status-header">
            {getStatusIcon(crawlingStatus)}
            <span className="status-name">Crawling</span>
            {crawlingUpdate?.message && (
              <span className="status-message">{crawlingUpdate.message}</span>
            )}
          </div>
        </div>

        {/* Validator Statuses */}
        {Object.entries(validatorMap).map(([name, update]) => {
          const isExpanded = expandedValidators.has(name)
          
          return (
            <div key={name} className={`status-item validator ${update.status}`}>
              <div 
                className="status-header clickable"
                onClick={() => toggleValidator(name)}
              >
                {getStatusIcon(update.status)}
                <span className="status-name">{name}</span>
                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
              </div>
              
              {isExpanded && update.details && (
                <div className="status-details">
                  <div className="details-header">
                    <span className={`result-badge ${update.details.passed ? 'passed' : 'failed'}`}>
                      {update.details.passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                  <pre className="details-output">{update.details.output}</pre>
                </div>
              )}
            </div>
          )
        })}

        {/* Error Status */}
        {errorUpdate && (
          <div className="status-item error">
            <div className="status-header">
              <span className="icon-failed">✗</span>
              <span className="status-name">Error</span>
              <span className="status-message">{errorUpdate.message}</span>
            </div>
          </div>
        )}

        {/* Completion Summary */}
        {completionUpdate && (
          <div className="completion-summary">
            <h3>Scan Complete</h3>
            <p className="completion-message">{completionUpdate.message}</p>
            {completionUpdate.details && (
              <div className="completion-stats">
                <div className="stat">
                  <span className="stat-label">Passed:</span>
                  <span className="stat-value passed">{completionUpdate.details.passed}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Total:</span>
                  <span className="stat-value">{completionUpdate.details.total}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default StatusDisplay
