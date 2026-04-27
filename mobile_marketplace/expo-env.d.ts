/// <reference types="expo/types" />

declare module '*.png' {
  const value: number;
  export default value;
}

declare module '*.jpg' {
  const value: number;
  export default value;
}

declare module '*.json' {
  const value: Record<string, unknown>;
  export default value;
}

declare module '*.ttf' {
  const value: number;
  export default value;
}
