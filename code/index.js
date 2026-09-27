const API_URL = 'http://10.86.245.186:5000/analyze'

Page({
  data: {
    imagePath: '',
    imageBase64: '',
    loading: false,
    result: '',
    errorMsg: ''
  },

  // ========== 选图 ==========
  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sizeType: ['compressed'],   // 让系统先压一次
      sourceType: ['camera', 'album'],
      success: (res) => {
        const file = res.tempFiles[0]
        const sizeMB = file.size / 1024 / 1024
        console.log('选图大小:', sizeMB.toFixed(2), 'MB')

        // 大于 1MB 再压一次
        if (sizeMB > 1) {
          wx.compressImage({
            src: file.tempFilePath,
            quality: 70,
            success: (r) => {
              this.setData({
                imagePath: r.tempFilePath,
                result: '',
                errorMsg: ''
              })
            },
            fail: () => {
              this.setData({
                imagePath: file.tempFilePath,
                result: '',
                errorMsg: ''
              })
            }
          })
        } else {
          this.setData({
            imagePath: file.tempFilePath,
            result: '',
            errorMsg: ''
          })
        }
      },
      fail: (err) => {
        console.warn('选图取消或失败:', err)
      }
    })
  },

  // ========== 开始分析 ==========
  analyzeImage() {
    if (!this.data.imagePath) {
      wx.showToast({ title: '请先选一张图', icon: 'none' })
      return
    }
    if (this.data.loading) return

    this.setData({ loading: true, result: '', errorMsg: '' })

    // 1. 转 base64
    wx.getFileSystemManager().readFile({
      filePath: this.data.imagePath,
      encoding: 'base64',
      success: (fileRes) => {
        const b64 = fileRes.data
        console.log('base64 长度:', b64.length)

        // 2. 请求后端
        wx.request({
          url: API_URL,
          method: 'POST',
          header: { 'content-type': 'application/json' },
          timeout: 120000,   // 120 秒
          data: { image_base64: b64 },

          success: (res) => {
            console.log('后端返回:', res.data)
            if (res.statusCode === 200 && res.data && res.data.result) {
              this.setData({ result: res.data.result })
            } else {
              this.setData({
                errorMsg: (res.data && res.data.error) || '分析失败，请重试'
              })
            }
          },

          fail: (err) => {
            console.error('请求失败:', err)
            this.setData({ errorMsg: '网络异常，请检查后端服务是否启动' })
          },

          complete: () => {
            this.setData({ loading: false })
          }
        })
      },
      fail: (err) => {
        console.error('读图失败:', err)
        this.setData({ loading: false, errorMsg: '图片读取失败，请重选' })
      }
    })
  }
})
