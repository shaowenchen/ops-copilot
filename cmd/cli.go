package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

var rootCmd = &cobra.Command{
	Use:   "ops-copilot",
	Short: "AI-powered DevOps assistant",
	Long:  `Ops-copilot is an AI-powered DevOps assistant that helps you with operations tasks using LLM.`,
}
