import React from 'react';

const ModelSelection = ({ models, selectedModel, setSelectedModel, currentModel, isLoadingModel }) => {
  const handleModelChange = (event) => {
    setSelectedModel(event.target.value);
  };

  return (
    <div className="model-selection-container d-flex justify-content-end flex-wrap">
      {isLoadingModel && <div className='spinner' style={{marginLeft: '0px', marginRight: '10px'}}></div>}
      <select id='model-select' className='form-select' onChange={handleModelChange} value={selectedModel}>
        {models.map((model, index) => (
          <option key={index} value={model}>{model}</option>
        ))}
      </select>
    </div>
  );
};

export default ModelSelection;