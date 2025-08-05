# BRAG [MCP] Electron App

This is an Electron desktop application for managing RAG (Retrieval-Augmented Generation) data sources.

## Prerequisites

- Node.js (v22.9.0 or higher recommended)
- npm or yarn
- macOS (for building Mac apps)

## Development

### Install Dependencies

```bash
npm install
```

### Run in Development Mode

```bash
npm run dev
```

This will start the Electron app with hot-reload enabled.

### Backend Server

The app expects a backend server running at `http://localhost:8000`. Make sure to start your backend server before using the app's features.

## Building

### Build for Production

```bash
npm run build
```

### Package for macOS

```bash
npm run make
```

This will create:

- A `.zip` file for distribution
- A `.dmg` installer for macOS
- The packaged app in the `out` directory

### Code Signing (Optional)

For distributing on macOS, you may want to code sign and notarize your app. Set these environment variables:

```bash
export APPLE_ID="your-apple-id@example.com"
export APPLE_PASSWORD="your-app-specific-password"
export APPLE_TEAM_ID="your-team-id"
```

## Scripts

- `npm run dev` - Start the app in development mode
- `npm run build` - Build the app for production
- `npm run start` - Start the built app
- `npm run package` - Package the app without creating installers
- `npm run make` - Create platform-specific installers
- `npm run typecheck` - Run TypeScript type checking
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier

## Architecture

- **Main Process** (`electron/main.ts`) - Manages app windows and system integration
- **Preload Script** (`electron/preload.ts`) - Provides secure API bridge to renderer
- **Renderer Process** (`src/`) - React application UI
- **Main Component** (`src/components/DataSourcesView.tsx`) - The main application interface

## Features

- View and manage data sources
- Add files or directories for processing
- View vector statistics and indexing status
- Dark mode support
- Native file picker integration
