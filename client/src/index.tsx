/// <reference path="global-interfaces.d.ts" />
/// <reference path="types.d.ts" />

import * as React from 'react';
import * as ReactDOM from 'react-dom/client';
import { createRoot } from 'react-dom/client';

import { BrowserApp } from './browser-app';

import '../styles/main.scss';
import 'material-symbols';

export { Application } from './application';
export * from './app-backends/base';
export * from './app-backends/browser';
export * from './backends/common';
export { MessageBackend } from './backends/message';
export * from './contexts';
export * from './draft';
export * from './format';
export * from './host';
export { Startup } from './startup';
export * from './components/icon';
export * as Form from './components/standard-form';
export { Pool } from './util';
export * as util from './util';
export { React, ReactDOM };

export * from './dynamic-value';
export * from './geometry';
export * from './components/button';
export * from './components/context-menu';
export * from './components/description';
export * from './components/diagnostics-report';
export * from './components/features';
export * from './components/graph-editor';
export * from './components/large-icon';
export * from './components/progress-bar';
export * from './components/timed-progress-bar';
export * from './components/item-list';
export * from './components/selector';
export * from './unit';

export * from './interfaces/host';
export * from './interfaces/graph';
export * from './interfaces/protocol';
export * from './interfaces/unit';
export * from './interfaces/view';


export function createBrowserApp(element: Element) {
  let root = createRoot(element);
  root.render(<BrowserApp />);
}
