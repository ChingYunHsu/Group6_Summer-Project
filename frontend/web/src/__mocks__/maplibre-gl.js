const maplibregl = {
  Map: jest.fn().mockImplementation(() => ({
    addControl: jest.fn(),
    remove: jest.fn(),
    on: jest.fn(),
    off: jest.fn(),

    getLayer: jest.fn(() => null),
    removeLayer: jest.fn(),

    getSource: jest.fn(() => null),
    removeSource: jest.fn(),

    addLayer: jest.fn(),
    addSource: jest.fn(),
  })),

  Marker: jest.fn().mockImplementation(() => ({
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
  })),

  Popup: jest.fn().mockImplementation(() => ({
    setHTML: jest.fn().mockReturnThis(),
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
  })),

  NavigationControl: jest.fn(),
};

module.exports = maplibregl;