package main

import (
	"bufio"
	"encoding/binary"
	"flag"
	"fmt"
	"log"
	"net"
	"net/url"
	"os"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

// -------- Config --------
type Config struct {
	Host         string
	Port         int
	TestID       string
	ClientCount  int
	MessageCount int
	IntervalMs   int
	MessageSize  int
	TimeoutMs    int
}

// -------- Log Event --------
type LogEvent struct {
	ConnID     int32
	Index      int32
	LatencyMs  float64
	SentAt     int64
	ReceivedAt int64
}

var (
	logChan   chan LogEvent
	connIndex int32
)

func main() {
	runtime.GOMAXPROCS(4)

	cfg := parseFlags()

	log.Printf("========================================")
	log.Printf("TEST %s BAŞLIYOR", cfg.TestID)
	log.Printf("Port: %d", cfg.Port)
	log.Printf("Client Sayısı: %d", cfg.ClientCount)
	log.Printf("Mesaj Boyutu: %d byte", cfg.MessageSize)
	log.Printf("Interval: %d ms", cfg.IntervalMs)
	log.Printf("Timeout: %d ms", cfg.TimeoutMs)
	log.Printf("Toplam Beklenen Mesaj (Loglanacak): %d", cfg.ClientCount*(cfg.MessageCount-5))
	log.Printf("========================================")

	logChan = make(chan LogEvent, 200_000)

	logFile := fmt.Sprintf("client_log_%s.csv", cfg.TestID)
	f, err := os.Create("/logs/" + logFile)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	writer := bufio.NewWriterSize(f, 8*1024*1024)
	writer.WriteString("test_id,conn_id,index,latency_ms,sent_at,received_at,interval,timeout_ms,message_size\n")

	go logWriter(writer, cfg)

	var wg sync.WaitGroup
	startBarrier := make(chan struct{})

	for i := 0; i < cfg.ClientCount; i++ {
		wg.Add(1)
		go wsClient(cfg, &wg, startBarrier)
	}

	close(startBarrier)

	wg.Wait()
	close(logChan)

	time.Sleep(500 * time.Millisecond)
	writer.Flush()
	f.Sync()
}

func parseFlags() Config {
	var cfg Config

	flag.StringVar(&cfg.Host, "host", "localhost", "ws host")
	flag.IntVar(&cfg.Port, "port", 8080, "ws port")
	flag.StringVar(&cfg.TestID, "test-id", "1", "test id")
	flag.IntVar(&cfg.ClientCount, "clients", 1, "client count")
	flag.IntVar(&cfg.MessageCount, "messages", 10005, "message count")
	flag.IntVar(&cfg.IntervalMs, "interval", 1, "interval ms")
	flag.IntVar(&cfg.MessageSize, "message-size", 1024, "message size bytes")
	flag.IntVar(&cfg.TimeoutMs, "timeout", 1000, "timeout ms (read/write)")

	flag.Parse()
	return cfg
}

func wsClient(cfg Config, wg *sync.WaitGroup, start <-chan struct{}) {
	defer wg.Done()

	id := atomic.AddInt32(&connIndex, 1)

	u := url.URL{Scheme: "ws", Host: fmt.Sprintf("%s:%d", cfg.Host, cfg.Port), Path: "/ws"}

	dialer := websocket.Dialer{
		ReadBufferSize:    72000,
		WriteBufferSize:   72000,
		EnableCompression: false,
	}

	c, _, err := dialer.Dial(u.String(), nil)

	if err != nil {
		//log.Printf("dial error: %v", err)
		return
	}
	defer c.Close()

	tcpConn, ok := c.UnderlyingConn().(*net.TCPConn)
	if ok {
		if err := tcpConn.SetNoDelay(true); err != nil {
			log.Printf("TCP_NODELAY error: %v", err)
		}
	}

	tid, _ := strconv.Atoi(cfg.TestID)
	payload := []byte(strings.Repeat("X", cfg.MessageSize))
	ticker := time.NewTicker(time.Duration(cfg.IntervalMs) * time.Millisecond)
	timeout := time.Duration(cfg.TimeoutMs) * time.Millisecond

	defer ticker.Stop()

	<-start

	for i := 0; i < cfg.MessageCount; i++ {
		<-ticker.C

		binary.BigEndian.PutUint16(payload[0:2], uint16(tid))
		binary.BigEndian.PutUint16(payload[2:4], uint16(id))
		binary.BigEndian.PutUint32(payload[4:8], uint32(i))

		sendTime := time.Now()

		c.SetWriteDeadline(time.Now().Add(timeout))

		err := c.WriteMessage(websocket.BinaryMessage, payload)
		if err != nil {
			//log.Printf("write error conn %d: %v", id, err)
			return
		}

		c.SetReadDeadline(time.Now().Add(timeout))

		_, _, err = c.ReadMessage()
		if err != nil {
			//log.Printf("read error conn %d: %v", id, err)
			return
		}
		recvTime := time.Now()

		if i < 5 {
			continue
		}

		logIndex := int32(i)

		latencyMs := float64(recvTime.Sub(sendTime).Nanoseconds()) / 1e6

		logChan <- LogEvent{
			ConnID:     id,
			Index:      logIndex,
			LatencyMs:  latencyMs,
			SentAt:     sendTime.UnixNano(),
			ReceivedAt: recvTime.UnixNano(),
		}
	}
}

func logWriter(w *bufio.Writer, cfg Config) {
	buffer := make([]LogEvent, 0, 10_000)

	flush := func() {
		for _, ev := range buffer {
			fmt.Fprintf(w, "%s,%d,%d,%.6f,%d,%d,%d,%d,%d\n",
				cfg.TestID,
				ev.ConnID,
				ev.Index,
				ev.LatencyMs,
				ev.SentAt,
				ev.ReceivedAt,
				cfg.IntervalMs,
				cfg.TimeoutMs,
				cfg.MessageSize,
			)
		}
		buffer = buffer[:0]
	}

	for ev := range logChan {
		buffer = append(buffer, ev)
		if len(buffer) >= 10_000 {
			flush()
		}
	}

	if len(buffer) > 0 {
		flush()
	}
}
