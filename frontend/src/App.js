import React from 'react';
import PdfOcr from './components/PdfOcr';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Media Utils</h1>
      </header>

      <main>
        <PdfOcr />
      </main>
    </div>
  );
}

export default App;