// A response owns the UI only until another intent invalidates it.
export function createRequestGuard(){
  let version=0;
  return {
    invalidate(){version++;},
    capture(){const current=version;return ()=>current===version;},
  };
}
