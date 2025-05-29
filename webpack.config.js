const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
resolve: {
    extensions: ['.js', '.json', '.jsx', '.ts', '.tsx'],
    },
  mode: "development",
  entry: "./index.js",
  output: {
    path: path.resolve(__dirname, "dist"),
    filename: "bundle.js",
    clean: true,
  },
  devServer: {
    static: "./dist",
    port: 3000,
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: "index.html",
    }),
  ],
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: "babel-loader",
      },
    ],
  },
  module: {
    rules: [
      {
        test: /\.m?js$/,
        resolve: {
          fullySpecified: false, // allow imports without extensions in node_modules for .js/.mjs files
        },
        include: /node_modules\/@geoarrow\/deck\.gl-layers/,
      },
    ],
  },
};
