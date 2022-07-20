# Alab Management Dashboard 
This is the source code for Alab Management frontend.

## Setting up development environment
This repo uses `yarn` to manage packages. To install, please follow the instruction on their website.

### Installing packages
```shell
yarn install
```

### Add new packages
```shell
yarn add <package_name>
```

### Start developing server
```shell
# a server will serve the webpage
yarn start
```

### Build production version
```shell
# the production version will directly 
# be copied to ../alab_management/dashboard/ui
yarn build
```

## Add new page on the dashboard
1. Create a folder in [`src`](./src) folder to include all the source code of the page.
2. Add it to Nav bar [here](./src/App.js#L71). Follow the same format as the existing `NavLink`  
3. Add it to `Router` [here](./src/App.js#L76). Set `element` to the component you have written. Set path to a unique endpoint name.
4. Done!

## Backend programming
See [here](../alab_management/dashboard/routes). We use `Flask` as the backend. Just add one blueprint to include the endpoints you need.

- Remember to add blueprint to [\_\_init\_\_.py](../alab_management/dashboard/routes/__init__.py#L6)