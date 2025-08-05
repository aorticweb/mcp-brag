module.exports = {
  packagerConfig: {
    name: 'BRAG-MCP',
    icon: './src/images/icon',
    appBundleId: 'com.mcprag.app',
    appCategoryType: 'public.app-category.developer-tools',
    osxSign: false,
    osxNotarize: false,
    asar: true,
    extraResource: ['./server-dist/python', './server-dist/mcp_server.pyz'],
    afterCopy: [
      (buildPath, electronVersion, platform, arch, callback) => {
        const fs = require('fs');
        const path = require('path');

        if (platform === 'darwin' || platform === 'linux') {
          const serverPath = path.join(buildPath, 'resources', 'python');

          // Check if the file exists before trying to chmod
          if (fs.existsSync(serverPath)) {
            console.log(`Setting executable permissions for ${serverPath}`);
            try {
              fs.chmodSync(serverPath, 0o755);
            } catch (error) {
              console.error('Failed to set executable permissions:', error);
            }
          }
        }
        callback();
      },
    ],
  },
  rebuildConfig: {},
  makers: [
    {
      name: '@electron-forge/maker-squirrel',
      config: {},
    },
    {
      name: '@electron-forge/maker-zip',
      platforms: ['darwin'],
    },
    {
      name: '@electron-forge/maker-dmg',
      config: {
        name: 'BRAG-MCP',
        icon: './src/images/icon.icns',
        format: 'ULFO',
      },
      platforms: ['darwin'],
    },
    {
      name: '@electron-forge/maker-deb',
      config: {},
    },
    {
      name: '@electron-forge/maker-rpm',
      config: {},
    },
  ],
  plugins: [
    {
      name: '@electron-forge/plugin-vite',
      config: {
        // 1️⃣ Build targets that go into .vite/<something>
        build: [
          {
            entry: 'electron/main.ts', // main process
            config: 'electron.vite.config.ts',
          },
          {
            entry: 'electron/preload.ts', // 👈 preload process
            config: 'electron.vite.config.ts',
          },
        ],

        // 2️⃣ Renderer windows
        renderer: [
          {
            name: 'main_window',
            config: 'electron.vite.config.ts',
          },
        ],
      },
    },
    {
      name: '@electron-forge/plugin-auto-unpack-natives',
      config: {},
    },
  ],
};
