import React, { useState } from 'react';
import styles from './App.module.css';

const App = () => {
  const [text, setText] = useState('');

  const handleRecord = async () => {
    // TODO: implement MediaRecorder logic
  };

  const handleTextSubmit = () => {
    // TODO: POST to /embed-text
  };

  const handleCamera = async () => {
    // TODO: implement getUserMedia logic
  };

  const handleUpload = (e) => {
    // TODO: POST file to /upload
  };

  return (
    <main className={styles.main}>
      <div className={styles.grid}>
        <button className={styles.card} onClick={handleRecord}>
          Record Audio
        </button>
        <div className={`${styles.card} ${styles.textPrompt}`}> 
          <input
            className={styles.textInput}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text"
          />
          <button className={`${styles.card} ${styles.submitButton}`} onClick={handleTextSubmit}>
            Submit
          </button>
        </div>
        <button className={styles.card} onClick={handleCamera}>
          Camera Access
        </button>
        <label className={styles.card} htmlFor="file-upload" style={{ cursor: 'pointer' }}>
          File Upload
          <input
            id="file-upload"
            type="file"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
        </label>
      </div>
    </main>
  );
};

export default App;
