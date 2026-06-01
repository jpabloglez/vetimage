/**
 * OHIF Viewer Configuration
 *
 * This configuration file sets up the OHIF Viewer for the MedAI Platform
 * with DICOMweb data source pointing to our backend API.
 */

import { Types } from '@ohif/core';

// API Base URL - use environment variable or default to backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3080';

/**
 * OHIF Viewer Configuration Object
 */
const ohifConfig: Types.AppConfig = {
  /**
   * Viewer routing and display options
   */
  routerBasename: '/',

  /**
   * Show study list by default
   */
  showStudyList: true,

  /**
   * Data sources configuration
   * Points to our Django backend DICOMweb API
   */
  dataSources: [
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        friendlyName: 'MedAI Platform DICOM Server',
        name: 'medai',
        wadoUriRoot: `${API_BASE_URL}/api/dicom/dicom-web`,
        qidoRoot: `${API_BASE_URL}/api/dicom/dicom-web`,
        wadoRoot: `${API_BASE_URL}/api/dicom/dicom-web`,
        qidoSupportsIncludeField: false,
        supportsReject: false,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: false,
        supportsWildcard: false,
        staticWado: true,
        singlepart: 'bulkdata,video,pdf',
      },
    },
  ],

  /**
   * Extensions to load
   */
  extensions: [],

  /**
   * Modes configuration
   */
  modes: [],

  /**
   * Default data source
   */
  defaultDataSourceName: 'dicomweb',

  /**
   * Hotkeys configuration
   */
  hotkeys: [
    {
      commandName: 'incrementActiveViewport',
      label: 'Next Viewport',
      keys: ['right'],
    },
    {
      commandName: 'decrementActiveViewport',
      label: 'Previous Viewport',
      keys: ['left'],
    },
    {
      commandName: 'rotateViewportCW',
      label: 'Rotate Right',
      keys: ['r'],
    },
    {
      commandName: 'rotateViewportCCW',
      label: 'Rotate Left',
      keys: ['l'],
    },
    {
      commandName: 'invertViewport',
      label: 'Invert',
      keys: ['i'],
    },
    {
      commandName: 'flipViewportHorizontal',
      label: 'Flip Horizontally',
      keys: ['h'],
    },
    {
      commandName: 'flipViewportVertical',
      label: 'Flip Vertically',
      keys: ['v'],
    },
    {
      commandName: 'scaleUpViewport',
      label: 'Zoom In',
      keys: ['+'],
    },
    {
      commandName: 'scaleDownViewport',
      label: 'Zoom Out',
      keys: ['-'],
    },
    {
      commandName: 'fitViewportToWindow',
      label: 'Zoom to Fit',
      keys: ['='],
    },
    {
      commandName: 'resetViewport',
      label: 'Reset',
      keys: ['space'],
    },
    {
      commandName: 'nextImage',
      label: 'Next Image',
      keys: ['down'],
    },
    {
      commandName: 'previousImage',
      label: 'Previous Image',
      keys: ['up'],
    },
    {
      commandName: 'firstImage',
      label: 'First Image',
      keys: ['home'],
    },
    {
      commandName: 'lastImage',
      label: 'Last Image',
      keys: ['end'],
    },
  ],

  /**
   * Cornerstone extension configuration
   */
  cornerstoneExtensionConfig: {},

  /**
   * UI customization
   */
  whiteLabeling: {
    createLogoComponentFn: () => null, // Use custom logo from navbar
  },

  /**
   * Study prefetching
   */
  studyPrefetcher: {
    enabled: true,
    maxNumPrefetchRequests: 10,
  },
};

export default ohifConfig;

/**
 * Extension configurations
 */
export const extensionConfig = {
  // Default extension for basic viewing
  '@ohif/extension-default': {
    // Default tools configuration
  },

  // Cornerstone for image rendering
  '@ohif/extension-cornerstone': {
    tools: {
      // Window level tool
      WindowLevel: {
        mouse: {
          enabled: true,
        },
      },
      // Pan tool
      Pan: {
        mouse: {
          enabled: true,
        },
      },
      // Zoom tool
      Zoom: {
        mouse: {
          enabled: true,
        },
      },
      // Stack scroll
      StackScroll: {
        mouse: {
          enabled: true,
        },
      },
      // Length measurement
      Length: {
        mouse: {
          enabled: true,
        },
      },
      // Angle measurement
      Angle: {
        mouse: {
          enabled: true,
        },
      },
      // Rectangle ROI
      RectangleROI: {
        mouse: {
          enabled: true,
        },
      },
      // Elliptical ROI
      EllipticalROI: {
        mouse: {
          enabled: true,
        },
      },
      // Bidirectional measurement
      Bidirectional: {
        mouse: {
          enabled: true,
        },
      },
    },
  },
};

/**
 * Helper function to get API URL
 */
export const getApiUrl = (): string => {
  return API_BASE_URL;
};

/**
 * Helper function to get DICOMweb URL
 */
export const getDicomWebUrl = (): string => {
  return `${API_BASE_URL}/api/dicom/dicom-web`;
};
