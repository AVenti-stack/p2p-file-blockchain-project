{
  function popupNotification(eventTypeId, message, detailLink) {
    window.postMessage({
      type: 'TEAMCITY_NOTIFICATION',
      eventTypeId,
      message,
      detailLink,
    })
  }

  function overrideRefresh() {
    HTMLDivElement.prototype.refresh = (_, search) => {
      if (search != null) {
        window.postMessage({
          type: 'TEAMCITY_IS_ALIVE',
          url: window.base_uri,
        })
        location.search = search
      }
    }
  }

  if (window.Win32 != null && window.Win32.Extension != null) {
    window.Win32.Extension.popupNotification = popupNotification
    overrideRefresh()
  } else {
    let Extension
    const Win32 = {
      get Extension() {
        return Extension
      },
      set Extension(value) {
        value.popupNotification = popupNotification
        overrideRefresh()
        Extension = value
      },
    }

    Object.defineProperty(window, 'Win32', {
      get: () => Win32,
      set() {},
    })
  }
}
